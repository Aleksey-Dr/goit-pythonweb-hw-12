import crud
password = "secure_admin_password"
hashed_password = crud.get_password_hash(password)
print(hashed_password)

"""
headers={"Authorization": "Bearer valid_admin_token"}
headers={"Authorization": "Bearer test_token"}
"""