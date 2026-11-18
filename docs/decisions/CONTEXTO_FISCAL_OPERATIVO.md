# Documento Fiscal – Trading Cripto (Asalariado)

## 1. Contexto Fiscal

| Campo | Detalle |
|---|---|
| **Régimen** | Sueldos y Salarios (clave 605) |
| **Ingreso principal** | Salario full-time |
| **Actividad secundaria** | Swing trading cripto |
| **Instrumentos** | BTC/USDT |
| **Exchange** | Binance |
| **Frecuencia máxima** | 8 trades/mes (variable, no fijo) |
| **Ticket por trade** | $500 – $5,000 MXN (hasta $10,000 extraordinariamente) |
| **Exención aplicable** | Art. 93, XIX, b) LISR → $128,383.92 MXN/año (2026) |
| **ISR a cargo** | **$0** (bajo exención) |
| **Obligación** | Declaración anual (abril), sección "Enajenación de bienes" |
| **PFAE / RESICO** | No aplica |
| **Metodo de costo** | FIFO |
| **Tipo de cambio** | BCI (Banco de México) del día de operación |

## 2. Preferencias de Operación

| Campo | Detalle |
|---|---|
| **Estilo** | Swing trading |
| **Ventana de posición** | 2 días – 2 semanas |
| **Timeframe de señal** | D1 + H4 o H1 |
| **Pares** | BTC/USDT |
| **Límite mensual** | 8 trades (máximo, no mínimo) |
| **Gestión de riesgo** | 1.5% del capital por trade (máximo) |

## 3. Esquema de Base de Datos

**Motor:** SQLite (suficiente para <1000 filas/año)
**Archivo:** `trades.db`

```sql
CREATE TABLE trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_utc       TIMESTAMP NOT NULL,
    fecha_mxn       DATE NOT NULL,
    activo          VARCHAR(10) NOT NULL,
    accion          VARCHAR(4) NOT NULL CHECK(accion IN ('BUY','SELL')),
    cantidad        DECIMAL(18,8) NOT NULL,
    precio_usdt     DECIMAL(18,6) NOT NULL,
    monto_usdt      DECIMAL(18,4) NOT NULL,
    tc_mxn_usd      DECIMAL(10,6) NOT NULL,
    monto_mxn       DECIMAL(18,4) NOT NULL,
    comisiones_mxn  DECIMAL(10,4) DEFAULT 0,
    costo_acum_mxn  DECIMAL(18,4),
    ganancia_mxn    DECIMAL(18,4),
    metodo_costo    VARCHAR(10) DEFAULT 'FIFO',
    exchange        VARCHAR(20) DEFAULT 'Binance',
    order_id        VARCHAR(64) UNIQUE NOT NULL
);

CREATE INDEX idx_fecha ON trades(fecha_mxn);
CREATE INDEX idx_activo ON trades(activo);
CREATE INDEX idx_accion ON trades(accion);

-- Vista: resumen anual para declaración
CREATE VIEW resumen_anual AS
SELECT 
    EXTRACT(YEAR FROM fecha_mxn) AS anio,
    SUM(ganancia_mxn) AS ganancia_neta_mxn,
    COUNT(*) AS total_vendas,
    COUNT(CASE WHEN ganancia_mxn > 0 THEN 1 END) AS trades_ganancia,
    COUNT(CASE WHEN ganancia_mxn < 0 THEN 1 END) AS trades_perdida
FROM trades
WHERE accion = 'SELL'
GROUP BY EXTRACT(YEAR FROM fecha_mxn);

-- Vista: posición abierta (costo promedio actual)
CREATE VIEW posicion_abierta AS
SELECT 
    activo,
    SUM(CASE WHEN accion='BUY' THEN cantidad ELSE -cantidad END) AS cantidad_neta,
    SUM(CASE WHEN accion='BUY' THEN monto_mxn ELSE 0 END) 
      - COALESCE(SUM(CASE WHEN accion='SELL' THEN costo_acum_mxn ELSE 0 END), 0) 
      AS costo_acumulado_mxn
FROM trades
GROUP BY activo
HAVING cantidad_neta > 0;
```

## 4. Campos Críticos (auditoría SAT)

| Campo | Función |
|---|---|
| `fecha_utc` + `fecha_mxn` | Fecha del evento fiscal |
| `activo` | Bien enajenado |
| `accion` | Adquisición vs. enajenación |
| `cantidad` + `precio_usdt` | Base para cálculo |
| `tc_mxn_usd` | Conversión a moneda funcional (MXN) |
| `comisiones_mxn` | Reducen el precio de venta |
| `costo_acum_mxn` | Costo de adquisición (FIFO) |
| `ganancia_mxn` | Resultado fiscal del trade |
| `order_id` | Trazabilidad con Binance |
| `metodo_costo` | Consistencia del método (FIFO) |

## 5. Obligaciones Anuales

| Acción | Cuándo | Dónde |
|---|---|---|
| Exportar CSV de Binance | Enero (antes de abril) | Binance → Historial → Export |
| Cargar datos a `trades.db` | Enero | Local |
| Verificar `resumen_anual` | Febrero | Local |
| Presentar declaración anual | 15 feb – 30 abril | [sat.gob.mx](https://www.sat.gob.mx) → Anual PF |
| Reportar en "Enajenación de bienes" | Con la anual | Ganancia neta = $X MXN → ISR = $0 |

## 6. Notas

- **No declarar** la ganancia (aunque sea exenta) = multa de $2,050 a $25,360 MXN.
- **Binance reporta** al SAT vía CARF desde 2023.
- **Cada swap** (BTC→ETH) es un evento fiscal, no solo SELL→USDT, NO aplicar jamas. 
- **Método FIFO** debe ser consistente todo el año; no cambiar a promedio a mitad de ejercicio.
- Si el capital crece y los tickets suben a >$50,000 MXN, reevaluar riesgo de PFAE.

---

*Documento generado: noviembre 2026. No constituye asesoría fiscal.*
