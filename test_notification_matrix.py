import pytest
from src.shared.notifier import get_notification_action


# Casos de prueba basados en la tabla del usuario
# (prev, curr, is_first_run, esperado)
# esperado puede ser una tupla (enviar, tipo) o una lista de tuplas para secuencias
test_cases = [
    (None, "INCIDENTE", False, (True, "INCIDENTE")),
    ("INCIDENTE", "OK", False, (True, "RESOLVED")),
    ("INCIDENTE", "SYNCING", False, [(True, "RESOLVED"), (True, "SYNCING")]),
    ("OK", "SYNCING", False, (True, "SYNCING")),
    ("SYNCING", "OK", False, (True, "OK")),
    (None, "OK", True, (True, "OK")),
    ("OK", "OK", False, (False, None)),
    ("RESOLVED", "OK", False, (False, None)),
    ("OK", "RESOLVED", False, (False, None)),
]

@pytest.mark.parametrize("prev,curr,is_first_run,esperado", test_cases)
def test_get_notification_action(prev, curr, is_first_run, esperado):
    result = get_notification_action(prev, curr, is_first_run)
    # Si se espera una secuencia de acciones
    if isinstance(esperado, list):
        assert isinstance(result, list), f"Para {prev}->{curr} se esperaba una lista de acciones, pero fue {type(result)}"
        assert result == esperado, f"Para {prev}->{curr} se esperaba {esperado}, pero fue {result}"
    else:
        # Se espera una sola acción
        if isinstance(result, list):
            # Si la función devuelve lista pero solo se espera una acción, tomar la primera
            result = result[0]
        assert result == esperado, f"Para {prev}->{curr} se esperaba {esperado}, pero fue {result}"
