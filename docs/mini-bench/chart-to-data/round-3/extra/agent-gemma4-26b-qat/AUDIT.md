# What the agent-gemma4-26b-qat sessions could do, and did

Read from each session's event stream (`trace.json`, kept locally). `offered` is every tool the session had; a session has no file, shell or web tool unless it is listed here.

| figure | offered | called | outside the allowed set |
|---|---|---|---|
| AMIE-Cardiology pictures_3 | finish, look, record_chart | look x5, record_chart x4, finish x1 | none |
| AMIE-Mx pictures_14 | finish, look, record_chart | look x3, record_chart x1 | none |
| AgentMD pictures_4 | finish, look, record_chart | finish x40 | none |
| Cardiologent pictures_0 | finish, look, record_chart | finish x2 | none |
| Cardiologent pictures_2 | finish, look, record_chart | finish x1 | none |
| Cardiologent pictures_3 | finish, look, record_chart | look x1, record_chart x2, finish x1 | none |
| Cardiologent pictures_4 | finish, look, record_chart | finish x1 | none |
