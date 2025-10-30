from aiauto.suites.data_validation.run_ge import run_ge_suite

def test_data_validation_stub():
    res = run_ge_suite("aiauto/config/project.yaml")
    assert res.success
