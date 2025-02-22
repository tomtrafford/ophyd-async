from dataclasses import dataclass
from enum import Enum
from typing import Sequence, TypeVar

import numpy as np
import numpy.typing as npt

# import pydantic_numpy.typing as pnd
from typing_extensions import TypedDict


class PandaHdf5DatasetType(str, Enum):
    FLOAT_64 = "float64"
    UINT_32 = "uint32"


class DatasetTable(TypedDict):
    name: npt.NDArray[np.str_]
    hdf5_type: Sequence[PandaHdf5DatasetType]


class SeqTrigger(str, Enum):
    IMMEDIATE = "Immediate"
    BITA_0 = "BITA=0"
    BITA_1 = "BITA=1"
    BITB_0 = "BITB=0"
    BITB_1 = "BITB=1"
    BITC_0 = "BITC=0"
    BITC_1 = "BITC=1"
    POSA_GT = "POSA>=POSITION"
    POSA_LT = "POSA<=POSITION"
    POSB_GT = "POSB>=POSITION"
    POSB_LT = "POSB<=POSITION"
    POSC_GT = "POSC>=POSITION"
    POSC_LT = "POSC<=POSITION"


@dataclass
class SeqTableRow:
    repeats: int = 1
    trigger: SeqTrigger = SeqTrigger.IMMEDIATE
    position: int = 0
    time1: int = 0
    outa1: bool = False
    outb1: bool = False
    outc1: bool = False
    outd1: bool = False
    oute1: bool = False
    outf1: bool = False
    time2: int = 0
    outa2: bool = False
    outb2: bool = False
    outc2: bool = False
    outd2: bool = False
    oute2: bool = False
    outf2: bool = False


# class SeqTable(TypedDict):
#     repeats: NotRequired[pnd.Np1DArrayUint16]
#     trigger: NotRequired[Sequence[SeqTrigger]]
#     position: NotRequired[pnd.Np1DArrayInt32]
#     time1: NotRequired[pnd.Np1DArrayUint32]
#     outa1: NotRequired[pnd.Np1DArrayBool]
#     outb1: NotRequired[pnd.Np1DArrayBool]
#     outc1: NotRequired[pnd.Np1DArrayBool]
#     outd1: NotRequired[pnd.Np1DArrayBool]
#     oute1: NotRequired[pnd.Np1DArrayBool]
#     outf1: NotRequired[pnd.Np1DArrayBool]
#     time2: NotRequired[pnd.Np1DArrayUint32]
#     outa2: NotRequired[pnd.Np1DArrayBool]
#     outb2: NotRequired[pnd.Np1DArrayBool]
#     outc2: NotRequired[pnd.Np1DArrayBool]
#     outd2: NotRequired[pnd.Np1DArrayBool]
#     oute2: NotRequired[pnd.Np1DArrayBool]
#     outf2: NotRequired[pnd.Np1DArrayBool]


T = TypeVar("T", bound=np.generic)


# def seq_table_from_arrays(
#     *,
#     repeats: Optional[npt.NDArray[np.uint16]] = None,
#     trigger: Optional[Sequence[SeqTrigger]] = None,
#     position: Optional[npt.NDArray[np.int32]] = None,
#     time1: Optional[npt.NDArray[np.uint32]] = None,
#     outa1: Optional[npt.NDArray[np.bool_]] = None,
#     outb1: Optional[npt.NDArray[np.bool_]] = None,
#     outc1: Optional[npt.NDArray[np.bool_]] = None,
#     outd1: Optional[npt.NDArray[np.bool_]] = None,
#     oute1: Optional[npt.NDArray[np.bool_]] = None,
#     outf1: Optional[npt.NDArray[np.bool_]] = None,
#     time2: npt.NDArray[np.uint32],
#     outa2: Optional[npt.NDArray[np.bool_]] = None,
#     outb2: Optional[npt.NDArray[np.bool_]] = None,
#     outc2: Optional[npt.NDArray[np.bool_]] = None,
#     outd2: Optional[npt.NDArray[np.bool_]] = None,
#     oute2: Optional[npt.NDArray[np.bool_]] = None,
#     outf2: Optional[npt.NDArray[np.bool_]] = None,
# ) -> SeqTable:
#     """
#     Constructs a sequence table from a series of columns as arrays.
#     time2 is the only required argument and must not be None.
#     All other provided arguments must be of equal length to time2.
#     If any other argument is not given, or else given as None or empty,
#     an array of length len(time2) filled with the following is defaulted:
#     repeats: 1
#     trigger: SeqTrigger.IMMEDIATE
#     all others: 0/False as appropriate
#     """
#     assert time2 is not None, "time2 must be provided"
#     length = len(time2)
#     assert 0 < length < 4096, f"Length {length} not in range"

#     def or_default(
#         value: Optional[npt.NDArray[T]], dtype: Type[T], default_value: int = 0
#     ) -> npt.NDArray[T]:
#         if value is None or len(value) == 0:
#             return np.full(length, default_value, dtype=dtype)
#         return value

#     table = SeqTable(
#         repeats=or_default(repeats, np.uint16, 1),
#         trigger=trigger or [SeqTrigger.IMMEDIATE] * length,
#         position=or_default(position, np.int32),
#         time1=or_default(time1, np.uint32),
#         outa1=or_default(outa1, np.bool_),
#         outb1=or_default(outb1, np.bool_),
#         outc1=or_default(outc1, np.bool_),
#         outd1=or_default(outd1, np.bool_),
#         oute1=or_default(oute1, np.bool_),
#         outf1=or_default(outf1, np.bool_),
#         time2=time2,
#         outa2=or_default(outa2, np.bool_),
#         outb2=or_default(outb2, np.bool_),
#         outc2=or_default(outc2, np.bool_),
#         outd2=or_default(outd2, np.bool_),
#         oute2=or_default(oute2, np.bool_),
#         outf2=or_default(outf2, np.bool_),
#     )
#     for k, v in table.items():
#         size = len(v)  # type: ignore
#         if size != length:
#             raise ValueError(f"{k}: has length {size} not {length}")
#     return table
