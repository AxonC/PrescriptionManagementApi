# Authentication and Authorization Guide
Two methods of 'protecting' endpoints exist within the codebase.

## get_current_user
Using the `get_current_user` method will ensure that the token is valid
and that a token exists in general. No further validation will occur using
this method.

Example usage: 
```python
@app.get("/test",
    dependencies=[Depends(get_current_user)]
)
async def api_method():
    ...
```

## PermissionsChecker class
The permissions checker class will follow the steps of `get_current_user`.

In addition to this, it allows the consumer to define a list of permission
names which should be used to authorize a particular endpoint.

Example Usage:
```python
REQUIRED_PERMISSIONS = ['test.permission']
@app.get("/test", 
    dependencies=[Depends(PermissionsChecker(REQUIRED_PERMISSIONS))]
)
async def api_method():
    ...
```
This will mandate the `test.permission` when calling that endpoint.
Should the permission not be present for the user, a 403 status
code will be returned.