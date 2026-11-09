from dataclasses import dataclass
@dataclass
class CurrentUser:
    id: int
    email: str
    display_name: str
class AuthProvider:
    def get_current_user(self) -> CurrentUser:
        raise NotImplementedError
class LocalSingleUserProvider(AuthProvider):
    def __init__(self) -> None:
        self._user = CurrentUser(id=1, email="local@radar-lab", display_name="Local User")
    def get_current_user(self) -> CurrentUser:
        return self._user
_provider: AuthProvider = LocalSingleUserProvider()
def get_current_user() -> CurrentUser:
    return _provider.get_current_user()