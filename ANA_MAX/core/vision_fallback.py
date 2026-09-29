class MockVisionFallback:
    def scan(self, *args, **kwargs):
        return {"success": True, "data": "Stub"}
def get_vision_fallback():
    return MockVisionFallback()
