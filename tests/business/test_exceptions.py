from icm.business.exceptions import BusinessError


def test_business_error_carries_status_code_and_message():
    error = BusinessError(404, "User not found")
    assert error.status_code == 404
    assert error.message == "User not found"
    assert str(error) == "User not found"
