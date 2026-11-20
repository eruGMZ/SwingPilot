"""Normalización sin contaminación (FEAT-017; REQ-G-102; TC-ML-003).

Las estadísticas se ajustan una sola vez y solo con datos de Train; Validation, OOS y LOCKBOX
se transforman con esas mismas estadísticas, sin recalcular. QA3-13: la pertenencia a Train se
comprueba con los datos (todas las filas con `open_time` < corte Train/Val del manifiesto), no
con una etiqueta.
"""
import pandas as pd


class ScalerError(RuntimeError):
    pass


class TrainOnlyScaler:
    def __init__(self):
        self.mean_: pd.Series | None = None
        self.std_: pd.Series | None = None
        self.columns_: list[str] | None = None
        self.train_end_ms: int | None = None

    def fit(self, df: pd.DataFrame, *, columns: list[str], train_end_ms: int,
            time_col: str = "open_time") -> "TrainOnlyScaler":
        if self.mean_ is not None:
            raise ScalerError("ya ajustado: no se reajusta")
        if time_col not in df.columns:
            raise ScalerError(f"falta la columna temporal {time_col!r} para comprobar la partición")
        if len(df) == 0:
            raise ScalerError("sin datos de Train")
        if int(df[time_col].max()) >= train_end_ms:
            raise ScalerError("los datos contienen filas posteriores al corte de Train (Validation/OOS/LOCKBOX)")
        self.columns_ = list(columns)
        self.mean_ = df[self.columns_].mean(skipna=True)
        self.std_ = df[self.columns_].std(ddof=0, skipna=True).replace(0, 1.0)
        self.train_end_ms = train_end_ms
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.mean_ is None:
            raise ScalerError("sin ajustar")
        return (df[self.columns_] - self.mean_) / self.std_
