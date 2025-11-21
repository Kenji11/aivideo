"""
Mock AI services for testing checkpoint creation.

These mocks return valid responses without making real API calls,
allowing for fast, cost-free testing of checkpoint logic.
"""


def mock_gpt4_response():
    """
    Return a valid spec structure from GPT-4 (Phase 1).

    Returns a complete video specification with template archetype,
    beat sequence, style, product, and audio configuration.
    """
    return {
        "selected_archetype": "luxury_showcase",
        "beat_sequence": [
            {"beat_id": "hero_shot", "duration": 10},
            {"beat_id": "detail_showcase", "duration": 10},
            {"beat_id": "call_to_action", "duration": 10}
        ],
        "style": {
            "aesthetic": "luxury",
            "mood": "sophisticated",
            "color_palette": ["gold", "black", "white"],
            "lighting": "cinematic"
        },
        "product": {
            "name": "Luxury Watch",
            "category": "watches",
            "features": ["Swiss movement", "Sapphire crystal", "Leather strap"]
        },
        "audio": {
            "music_style": "cinematic",
            "tempo": "moderate",
            "mood": "uplifting"
        },
        "duration": 30
    }


def mock_flux_image_url():
    """
    Return a mock image URL from FLUX (Phase 2).

    In real tests, this would be a temporary image file uploaded to S3.
    For mocking, returns a placeholder URL.
    """
    return "https://replicate.delivery/mock-flux-image-12345.png"


def mock_hailuo_video_url():
    """
    Return a mock video URL from Hailuo (Phase 3).

    In real tests, this would be a temporary video file uploaded to S3.
    For mocking, returns a placeholder URL.
    """
    return "https://replicate.delivery/mock-hailuo-video-67890.mp4"


def mock_kling_video_url():
    """
    Return a mock video URL from Kling (Phase 3 alternative).

    In real tests, this would be a temporary video file uploaded to S3.
    For mocking, returns a placeholder URL.
    """
    return "https://replicate.delivery/mock-kling-video-24680.mp4"


def mock_musicgen_audio_url():
    """
    Return a mock audio URL from MusicGen (Phase 4).

    In real tests, this would be a temporary audio file uploaded to S3.
    For mocking, returns a placeholder URL.
    """
    return "https://replicate.delivery/mock-musicgen-audio-13579.mp3"


class MockReplicateClient:
    """Mock Replicate client for testing."""

    def run(self, model: str, input: dict, **kwargs):
        """
        Mock the Replicate run method.

        Returns different mock URLs based on the model being called.

        Args:
            model: Model identifier (e.g., "black-forest-labs/flux-dev")
            input: Input parameters for the model
            **kwargs: Additional parameters

        Returns:
            Mock URL string appropriate for the model type
        """
        if "flux" in model.lower():
            return mock_flux_image_url()
        elif "hailuo" in model.lower():
            return mock_hailuo_video_url()
        elif "kling" in model.lower():
            return mock_kling_video_url()
        elif "musicgen" in model.lower():
            return mock_musicgen_audio_url()
        else:
            return "https://replicate.delivery/mock-output-00000.bin"


class MockOpenAIClient:
    """Mock OpenAI client for testing."""

    class ChatCompletion:
        """Mock chat completion."""

        class Choice:
            """Mock choice."""

            class Message:
                """Mock message."""

                def __init__(self, content: str):
                    self.content = content

            def __init__(self, content: str):
                self.message = self.Message(content)

        def __init__(self, content: str):
            self.choices = [self.Choice(content)]

    def __init__(self):
        self.chat = self

    def completions(self):
        """Mock completions method."""
        return self

    def create(self, **kwargs):
        """
        Mock the OpenAI chat completion create method.

        Returns a mock GPT-4 response with a valid spec structure.

        Args:
            **kwargs: Parameters (model, messages, temperature, etc.)

        Returns:
            Mock ChatCompletion with spec in JSON format
        """
        import json
        spec = mock_gpt4_response()
        return self.ChatCompletion(json.dumps(spec))


# Export mock instances
mock_replicate_client = MockReplicateClient()
mock_openai_client = MockOpenAIClient()
