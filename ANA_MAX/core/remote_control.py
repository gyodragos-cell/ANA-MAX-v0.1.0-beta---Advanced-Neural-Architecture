class MockRemoteManager:
    def execute(self, *args, **kwargs):
        return {"success": True, "data": "Stub"}
def get_remote_manager():
    return MockRemoteManager()
