"""H-2: Tests that emit is properly awaited in run_backtest."""
import ast
import inspect


def test_emit_complete_is_awaited():
    """H-2: emit(run_id, 'complete', 100) must be awaited in run_backtest."""
    from runner import backtest
    source = inspect.getsource(backtest.run_backtest)
    tree = ast.parse(source)

    found_awaited_emit = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Await):
            if isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == 'emit':
                    found_awaited_emit = True
                elif isinstance(call.func, ast.Attribute) and call.func.attr == 'emit':
                    found_awaited_emit = True

    assert found_awaited_emit, (
        "emit() call in run_backtest is not awaited — H-2 bug present"
    )
