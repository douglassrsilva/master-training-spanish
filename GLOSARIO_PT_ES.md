# Glosario oficial PT-BR → ES-LATAM — Databricks Master Training

Fuente de verdad para TODA la traducción (repo, slides, planilla). Cualquier identificador
técnico listado aquí DEBE usarse exactamente así en todos los archivos (SQL, notebooks, app,
READMEs). Si encuentras un identificador que no está aquí, tradúcelo con el mismo criterio y
regístralo en la sección "Agregados por los traductores" al final del archivo de tu entrega.

Idioma: español neutro de América Latina (tú/ustedes, nunca vosotros; "computadora", "celular",
"cobro/cobranza", "plan", "factura"). Mantener en inglés los nombres de producto y términos de
UI de Databricks (Unity Catalog, SQL Editor, Genie, Genie Code, Metric Views, AI/BI, Agent
Bricks, Supervisor Agent, Model Serving, Run all, Catalog Explorer, etc.).

## Objetos que NO cambian
- Catálogo `dbacademy`, schema compartido `churn`, grupo `dbacademy_workshop`,
  warehouse `dbacademy_workshop_wh`, cluster `dbacademy_workshop_cluster`.
- `feature_churn`, `churn_scores`, `modelo_churn`, `kb_volume`, `churn_flag`, `prob_churn`,
  `get_cliente_360`, `mvw_churn`, `id_cliente`, `id_ticket`, `id_uso`, `segmento`, `canal`,
  `categoria`, `csat`, `nps`, `mes`, `trimestre`, `dia_semana`, `logins_mes`, `horas_uso`,
  `funcionalidades_usadas`, `pago`, `dias_atraso`, `status`, `dim_cliente`.
- Empresa ficticia: **Conecta+**.
- Todos los NÚMEROS de los datos (2000 clientes, 1253 tickets, churn 0.27, corr -0.504 / 0.125,
  precios 49.9/89.9/149.9/299.9, AUC, etc.) se mantienen idénticos.

## Placeholders
| PT | ES |
|---|---|
| `<seu_schema>` / `<seu_database>` | `<tu_schema>` / `<tu_database>` |
| `<catálogo>` | `<catálogo>` |
| widget "Seu schema" | "Tu schema" |
| Regla del database: "Primeira letra do nome + último sobrenome — Whindersson Nunes → wnunes" | "Primera letra del nombre + primer apellido — Ejemplo: Gabriel García → ggarcia" |

## Tablas
| PT | ES |
|---|---|
| `dim_cliente` | `dim_cliente` |
| `dim_plano` | `dim_plan` |
| `dim_data` | `dim_fecha` |
| `fato_assinatura` | `hecho_suscripcion` |
| `fato_uso` | `hecho_uso` |
| `fato_faturamento` | `hecho_facturacion` |
| `fato_ticket_suporte` | `hecho_ticket_soporte` |
| prefijo "fato" (tabla de hechos) | "hecho" |

## Columnas
| Tabla | PT | ES |
|---|---|---|
| dim_cliente | nome_cliente | nombre_cliente |
| dim_cliente | cidade | ciudad |
| dim_cliente | uf (estado) | pais (código ISO de 2 letras) |
| dim_cliente | data_cadastro | fecha_registro |
| dim_cliente | canal_aquisicao | canal_adquisicion |
| dim_cliente | faixa_etaria | rango_edad |
| dim_fecha | data | fecha |
| dim_fecha | ano | anio |
| dim_fecha | nome_mes | nombre_mes |
| dim_fecha | fim_de_semana | fin_de_semana |
| dim_plan / varias | id_plano | id_plan |
| dim_plan / varias | nome_plano | nombre_plan |
| dim_plan | periodicidade | periodicidad |
| dim_plan / varias | preco_mensal | precio_mensual |
| hecho_suscripcion / hecho_facturacion | id_assinatura | id_suscripcion |
| hecho_suscripcion | data_inicio | fecha_inicio |
| hecho_suscripcion | data_fim | fecha_fin |
| hecho_suscripcion | motivo_cancelamento | motivo_cancelacion |
| hecho_facturacion | id_fatura | id_factura |
| hecho_facturacion / hecho_uso | competencia | periodo |
| hecho_facturacion | valor | monto |
| hecho_ticket_soporte | data_abertura | fecha_apertura |
| hecho_ticket_soporte | texto_reclamacao | texto_reclamo |
| feature_churn | uso_medio | uso_promedio |
| feature_churn | horas_medio | horas_promedio |
| feature_churn | dias_atraso_medio | dias_atraso_promedio |
| feature_churn | pct_faturas_atraso | pct_facturas_atraso |
| feature_churn | csat_medio | csat_promedio |
| feature_churn | nps_medio | nps_promedio |
| churn_scores | faixa_risco | nivel_riesgo |
| churn_scores | fator_principal | factor_principal |
| get_cliente_360 (salida) | anos_de_casa | anios_como_cliente |
| get_cliente_360 (salida) | desconto | descuento |
| get_cliente_360 (salida) | oferta_internet | oferta_internet |
| get_cliente_360 (salida) | oferta_fator | oferta_factor |
| consultas varias | taxa_churn | tasa_churn |
| consultas varias | receita | ingresos |
| consultas varias | inadimplencia | morosidad |
| constraints | pk_cliente / pk_plano / fk_{t}_cli | pk_cliente / pk_plan / fk_{t}_cli |

## Valores de datos (categorías)
| Campo | PT | ES |
|---|---|---|
| segmento | Consumidor / PME / Corporativo | Consumidor / PyME / Corporativo |
| canal_adquisicion | Orgânico / Indicação / Mídia Paga / Parceiro | Orgánico / Referido / Medios Pagos / Socio |
| nombre_plan | Básico / Padrão / Premium / Empresarial | Básico / Estándar / Premium / Empresarial |
| periodicidad | Mensal / Anual | Mensual / Anual |
| status | Ativa / Cancelada | Activa / Cancelada |
| motivo_cancelacion | Insatisfação / Preço / Concorrência / Atendimento / Mudança de necessidade | Insatisfacción / Precio / Competencia / Atención / Cambio de necesidad |
| canal (ticket) | Chat / Email / Telefone | Chat / Email / Teléfono |
| categoria (ticket) | Dúvida / Cobrança / Cancelamento / Técnico | Consulta / Cobranza / Cancelación / Técnico |
| nivel_riesgo | Alto / Médio / Baixo | Alto / Medio / Bajo |
| factor_principal | Baixo uso / Inadimplência / Insatisfação (CSAT) / Detrator (NPS) | Bajo uso / Morosidad / Insatisfacción (CSAT) / Detractor (NPS) |
| nombre_mes | janeiro … dezembro | enero … diciembre |
| moneda | R$ / reais | US$ / dólares (USD) |

## Geografía (Brasil → LATAM, mapeo 1:1 que preserva las distribuciones)
| Ciudad PT | UF | → Ciudad ES | pais | Región PT → Región ES |
|---|---|---|---|---|
| São Paulo | SP | Ciudad de México | MX | Sudeste → México |
| Rio de Janeiro | RJ | Guadalajara | MX | Sudeste → México |
| Belo Horizonte | MG | Monterrey | MX | Sudeste → México |
| Salvador | BA | Bogotá | CO | Nordeste → Andina |
| Fortaleza | CE | Lima | PE | Nordeste → Andina |
| Recife | PE | Quito | EC | Nordeste → Andina |
| Curitiba | PR | Buenos Aires | AR | Sul → Cono Sur |
| Porto Alegre | RS | Santiago | CL | Sul → Cono Sur |
| Brasília | DF | Santo Domingo | DO | Centro-Oeste → Caribe |
| Manaus | AM | San José | CR | Norte → Centroamérica |

- Agregado nacional "Brasil" → "LATAM". Regiones (orden): `["Centroamérica", "Andina", "Caribe", "México", "Cono Sur"]` (corresponde a Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
- Expresión de región en SQL (reemplaza la de `uf`):
  ```sql
  CASE WHEN c.pais IN ('MX') THEN 'México'
       WHEN c.pais IN ('CO','PE','EC','VE','BO') THEN 'Andina'
       WHEN c.pais IN ('AR','CL','UY','PY') THEN 'Cono Sur'
       WHEN c.pais IN ('DO','CU','PR') THEN 'Caribe'
       WHEN c.pais IN ('CR','PA','GT','HN','SV','NI') THEN 'Centroamérica' END
  ```
- Componente del mapa `MapaBrasil` → `MapaLatam`.

## Personas (nombres de clientes en datos y textos)
Nombres: Rafael→Alejandro, Ana→Ana, Nuno→Andrés, Diego→Diego, Carla→Carla, Lucas→Mateo,
Felipe→Felipe, Karina→Valentina, Sofia→Sofía, Elaine→Camila, Marina→Mariana, João→Juan,
Gabriela→Gabriela, Quezia→Ximena, Bruno→Santiago, Paulo→Pablo, Henrique→Javier, Olívia→Lucía,
Isabela→Isabella, Tiago→Sebastián.
Apellidos: Oliveira→García, Cardoso→Rodríguez, Carvalho→Martínez, Gomes→Gómez, Ribeiro→López,
Souza→Hernández, Lima→Pérez, Melo→Sánchez, Martins→Ramírez, Ferreira→Torres, Barbosa→Flores,
Costa→Rivera, Silva→Díaz, Araújo→Morales, Teixeira→Castro, Moraes→Ortiz, Rocha→Vargas,
Pereira→Romero, Almeida→Herrera, Santos→Jiménez.
(Ej.: "Rafael Oliveira" → "Alejandro García"). PII en tickets: teléfonos brasileños → formato
México (+52 …), email `cNNNNN@exemplo.com.br` → `cNNNNN@ejemplo.com`.

## Textos de tickets (10 plantillas)
| PT | ES |
|---|---|
| Preciso atualizar meus dados cadastrais, meu telefone é (31) 99888-7777. | Necesito actualizar mis datos de registro, mi teléfono es +52 81 9988 7777. |
| Como faço para alterar meu plano? Podem me contatar no <EMAIL>. | ¿Cómo hago para cambiar mi plan? Pueden contactarme en <EMAIL>. |
| Muito bom o suporte de vocês, parabéns pela equipe. | Muy bueno el soporte de ustedes, felicitaciones al equipo. |
| Atendimento excelente, resolveram meu problema rapidamente. Obrigado, <NOME>! | Atención excelente, resolvieron mi problema rápidamente. ¡Gracias, <NOMBRE>! |
| Gostaria de tirar uma dúvida sobre a minha fatura deste mês. | Quisiera hacer una consulta sobre mi factura de este mes. |
| Estou satisfeito com o serviço, tudo funcionando bem. | Estoy satisfecho con el servicio, todo funciona bien. |
| Péssimo atendimento. Se não resolverem vou cancelar e migrar para o concorrente. | Pésima atención. Si no lo resuelven voy a cancelar y pasarme a la competencia. |
| Serviço caindo toda hora, um absurdo. Meu email é <EMAIL> e ainda não recebi retorno. | El servicio se cae a cada rato, es un absurdo. Mi email es <EMAIL> y todavía no recibo respuesta. |
| Já pedi cancelamento e continuam cobrando. Falar com <NOME> no telefone 21 3344-5566. | Ya pedí la cancelación y me siguen cobrando. Hablar con <NOMBRE> al teléfono +52 33 3344 5566. |
| Estou muito insatisfeito. Liguei várias vezes para (11) 98765-4321 e ninguém resolve meu problema. | Estoy muy insatisfecho. Llamé varias veces al +52 55 9876 5432 y nadie resuelve mi problema. |

## Metric Views (Ex. 3)
| PT | ES |
|---|---|
| `mvw_churn` | `mvw_churn` |
| `mvw_receita` | `mvw_ingresos` |
| `mvw_suporte` | `mvw_soporte` |
| Dimensiones: Segmento, Plano, Mês, Canal, Categoria | Segmento, Plan, Mes, Canal, Categoría |
| Medidas: Cancelamentos, Clientes, Taxa de Churn | Cancelaciones, Clientes, Tasa de Churn |
| Medidas: Receita, Inadimplência, Ticket Médio | Ingresos, Morosidad, Ticket Promedio |
| Medidas: Tickets, CSAT Médio, NPS Médio | Tickets, CSAT Promedio, NPS Promedio |
| join aliases `cliente`, `plano` | `cliente`, `plan` |

## UC Functions (Ex. 8)
| PT | ES |
|---|---|
| `get_cliente_360` | `get_cliente_360` |
| `gerar_email_retencao` | `generar_email_retencion` |

## Base de conocimiento (kb_volume)
| PT | ES |
|---|---|
| FAQ_Atendimento.md | FAQ_Atencion.md |
| Politica_Retencao.md | Politica_Retencion.md |
| Playbook_Customer_Success.md | Playbook_Customer_Success.md |

## Genies / Agentes (Ex. 7) y App (Ex. 9)
| PT | ES |
|---|---|
| Genie de Faturamento | Genie de Facturación |
| Genie de Suporte | Genie de Soporte |
| Agente Supervisor | Agente Supervisor |
| Central de Retenção (app) | Central de Retención |
| Cockpit / Assistente / Retenção (pestañas) | Cockpit / Asistente / Retención |
| Agente Financeiro / Agente Suporte (slides) | Agente Financiero / Agente Soporte |

## Carpetas de módulos
| PT | ES |
|---|---|
| 00 - Setup and teardown | 00 - Setup y teardown |
| 00 - Setup and teardown/Setup guiado | 00 - Setup y teardown/Setup guiado |
| 01 - SQL com IA | 01 - SQL con IA |
| 02 - Geração de Alertas | 02 - Generación de Alertas |
| 03 - Métricas de Negócio | 03 - Métricas de Negocio |
| 04 - IA Generativa no SQL | 04 - IA Generativa en SQL |
| 05 - Dashboards com IA | 05 - Dashboards con IA |
| 06 - Previsão de Churn (ML) | 06 - Predicción de Churn (ML) |
| 07 - Análise de Dados Multi-Agent | 07 - Análisis de Datos Multi-Agent |
| 08 - Retenção com ML e GenAI | 08 - Retención con ML y GenAI |
| 09 - Criação de Apps | 09 - Creación de Apps |
| 10 - Fechamento (Próximos Passos) | 10 - Cierre (Próximos Pasos) |
| assets/01 - catálogo+schema no SQL Editor.png | assets/01 - catálogo+schema en SQL Editor.png |
| "Ex. N" / "Exercício N" / "Laboratório N" | "Ej. N" / "Ejercicio N" / "Laboratorio N" |

## Repositorio
- Repositorio en español: `douglassrsilva/master-training-spanish`.
- Los CSV se leen **desde la carpeta `data/` del propio Git folder** en el workspace (el repo
  EMU no es público, así que la URL raw de GitHub no funciona desde el cluster).
