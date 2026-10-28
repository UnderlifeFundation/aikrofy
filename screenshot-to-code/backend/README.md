# Run the type checker

> [!NOTE]
> **Estado Actual del Proyecto:** La plataforma ha sido unificada bajo la marca **Aikrofy**. Ya no se divide el proyecto en dos interfaces o proyectos independientes (PymAI y Executiv Enterprise); todo está integrado en la plataforma única **Aikrofy** con el dominio **aikrofy.com**. La IA o copiloto técnico integrado del sistema se denomina **Krof**.


poetry run pyright

# Run tests

poetry run pytest

## Prompt Summary

Use `print_prompt_summary` from `utils.py` to quickly visualize prompts:

```python
from utils import print_prompt_summary
print_prompt_summary(prompt_messages)
```
