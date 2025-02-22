import time

import numpy as np
import numpy.typing as npt
from bluesky.protocols import Flyable, Preparable
from pydantic import BaseModel, Field
from scanspec.specs import Line, Path, fly

from ophyd_async.core.async_status import AsyncStatus, WatchableAsyncStatus
from ophyd_async.core.signal import observe_value
from ophyd_async.core.utils import WatcherUpdate
from ophyd_async.epics.motion import Motor
from ophyd_async.epics.pmac import Pmac

TICK_S = 0.000001


class FlyTrajectoryInfo(BaseModel):
    """Minimal set of information required to fly a trajectory:"""

    #: Absolute position of the motor once it finishes accelerating to desired
    #: velocity, in motor EGUs
    start_position: float = Field(frozen=True)

    #: Absolute position of the motor once it begins decelerating from desired
    #: velocity, in EGUs
    end_position: float = Field(frozen=True)

    num_positions: int = Field(frozen=True)

    #: Time taken for the motor to get from start_position to end_position, excluding
    #: run-up and run-down, in seconds.
    time_per_position: float = Field(frozen=True, gt=0)


class PmacTrajectory(Pmac, Flyable, Preparable):
    """Device that moves a PMAC Motor record"""

    def __init__(self, prefix: str, cs: int, motor: Motor, name="") -> None:
        # Make a dict of which motors are for which cs axis
        self._fly_start: float
        self.cs = cs
        self.motor = motor
        super().__init__(prefix, cs, name=name)

    async def _ramp_up_velocity_pos(
        self, velocity: float, motor: Motor, end_velocity: float
    ):
        # Assuming ramping to or from 0
        max_velocity_acceleration_time = await motor.acceleration_time.get_value()
        max_velocity = await motor.max_velocity.get_value()
        delta_v = abs(end_velocity - velocity)
        accl_time = max_velocity_acceleration_time * delta_v / max_velocity
        disp = 0.5 * (velocity + end_velocity) * accl_time
        return [disp, accl_time]

    @AsyncStatus.wrap
    async def prepare(self, value: FlyTrajectoryInfo):
        # Which Axes are in use?

        spec = fly(
            Line(
                self.motor,
                value.start_position,
                value.end_position,
                value.num_positions,
            ),
            value.time_per_position,
        )
        stack = spec.calculate()
        path = Path(stack)
        chunk = path.consume()
        scan_size = len(chunk)
        scan_axes = chunk.axes()

        cs_ports = set()
        positions: dict[int, npt.NDArray[np.float64]] = {}
        velocities: dict[int, npt.NDArray[np.float64]] = {}
        time_array: npt.NDArray[np.float64] = []
        cs_axes: dict[Motor, int] = {}
        for axis in scan_axes:
            if axis != "DURATION":
                cs_port, cs_index = await self.get_cs_info(axis)
                positions[cs_index] = []
                velocities[cs_index] = []
                cs_ports.add(cs_port)
                cs_axes[axis] = cs_index
        assert len(cs_ports) == 1, "Motors in more than one CS"
        cs_port = cs_ports.pop()
        self.scantime = sum(chunk.midpoints["DURATION"])

        # Calc Velocity

        for axis in scan_axes:
            for i in range(scan_size):
                if axis != "DURATION":
                    velocities[cs_axes[axis]].append(
                        (chunk.upper[axis][i] - chunk.lower[axis][i])
                        / (chunk.midpoints["DURATION"][i])
                    )
                    positions[cs_axes[axis]].append(chunk.midpoints[axis][i])
                else:
                    time_array.append(int(chunk.midpoints[axis][i] / TICK_S))

        # Calculate Starting and end Position to allow ramp up and trail off velocity
        self.initial_pos = {}
        run_up_time = 0
        final_time = 0
        for axis in scan_axes:
            if axis != "DURATION":
                run_up_disp, run_up_t = await self._ramp_up_velocity_pos(
                    0,
                    axis,
                    velocities[cs_axes[axis]][0],
                )
                self.initial_pos[cs_axes[axis]] = (
                    positions[cs_axes[axis]][0] - run_up_disp
                )
                # trail off position and time
                if velocities[cs_axes[axis]][0] == velocities[cs_axes[axis]][-1]:
                    final_pos = positions[cs_axes[axis]][-1] + run_up_disp
                    final_time = run_up_t
                else:
                    ramp_down_disp, ramp_down_time = await self._ramp_up_velocity_pos(
                        velocities[cs_axes[axis]][-1],
                        axis,
                        0,
                    )
                    final_pos = positions[cs_axes[axis]][-1] + ramp_down_disp
                    final_time = max(ramp_down_time, final_time)
                positions[cs_axes[axis]].append(final_pos)
                velocities[cs_axes[axis]].append(0)
                run_up_time = max(run_up_time, run_up_t)

        self.scantime += run_up_time + final_time
        time_array[0] += run_up_time / TICK_S
        time_array.append(int(final_time / TICK_S))

        for axis in scan_axes:
            if axis != "DURATION":
                self.profile_cs_name.set(cs_port)
                self.points_to_build.set(scan_size + 1)
                self.use_axis[cs_axes[axis] + 1].set(True)
                self.positions[cs_axes[axis] + 1].set(positions[cs_axes[axis]])
                self.velocities[cs_axes[axis] + 1].set(velocities[cs_axes[axis]])
            else:
                self.time_array.set(time_array)

        # MOVE TO START
        for axis in scan_axes:
            if axis != "DURATION":
                await axis.set(self.initial_pos[cs_axes[axis]])

        # Set PMAC to use Velocity Array
        self.profile_calc_vel.set(False)

        self.build_profile.set(True)
        self._fly_start = time.monotonic()

    @AsyncStatus.wrap
    async def kickoff(self):
        self.status = self.execute_profile.set(1, timeout=self.scantime + 10)

    @WatchableAsyncStatus.wrap
    async def complete(self):
        async for percent in observe_value(self.scan_percent):
            yield WatcherUpdate(
                name=self.name,
                current=percent,
                initial=0,
                target=100,
                unit="%",
                precision=0,
                time_elapsed=time.monotonic() - self._fly_start,
            )
            if percent >= 100:
                break

    async def get_cs_info(self, motor: Motor) -> tuple[str, int]:
        output_link = await motor.output_link.get_value()
        # Split "@asyn(PORT,num)" into ["PORT", "num"]
        split = output_link.split("(")[1].rstrip(")").split(",")
        cs_port = split[0].strip()
        assert "CS" in cs_port, f"{self.name} not in a CS. It is not a compound motor."
        cs_index = int(split[1].strip()) - 1
        return cs_port, cs_index
