from dataclasses import dataclass, field

from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.pond_parameter_enum import PondParameters

@dataclass
class PondParametersHistoryModel:
    do: list[AnalysisReportModel] = field(default_factory=list)
    pH: list[AnalysisReportModel] = field(default_factory=list)
    tem: list[AnalysisReportModel] = field(default_factory=list)
    nh3: list[AnalysisReportModel] = field(default_factory=list)
    no2_n: list[AnalysisReportModel] = field(default_factory=list)
    salinity: list[AnalysisReportModel] = field(default_factory=list)

    def __post_init__(self) -> None:
        expected = {
            "do": PondParameters.DO,
            "pH": PondParameters.pH,
            "tem": PondParameters.tem,
            "nh3": PondParameters.NH3,
            "no2_n": PondParameters.NO2_N,
            "salinity": PondParameters.salinity,
        }
        for attr, parameter in expected.items():
            wrong = [r for r in getattr(self, attr) if r.parameter != parameter]
            if wrong:
                raise ValueError(
                    f"ประวัติช่อง '{attr}' ต้องเป็น {parameter.label} เท่านั้น "
                    f"แต่พบ {len(wrong)} รายการของ parameter อื่น "
                    f"(เช่น {wrong[0].parameter.label}) - ตรวจการ query ตาราง/การ map ข้อมูล"
                )