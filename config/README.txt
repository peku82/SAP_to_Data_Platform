config/
=======

Configuración del pipeline.

  .env.example  — plantilla con TODAS las variables. Copiar a .env y rellenar.
  .env          — credenciales reales (NO commitear, NO compartir).
  tables.yaml   — lista de tablas a extraer en Fase 1 y sus columnas clave
                  para deltas (UpdateDate, DocDate, CreateDate).

Nunca hacer commit de .env al repositorio.
