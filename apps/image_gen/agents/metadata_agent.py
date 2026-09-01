class MetadataAgent:
    @staticmethod
    def build(prompt):
        cleaned = " ".join(prompt.split())
        title = cleaned[:60] if cleaned else "AI Artwork"
        tag_candidates = [token.strip(".,!?").lower() for token in cleaned.split() if len(token) > 3]
        tags = list(dict.fromkeys(tag_candidates[:8]))
        description = f"AI-generated artwork based on prompt: {cleaned}" if cleaned else "AI-generated artwork"
        return {
            "title": title,
            "tags": tags,
            "description": description,
        }
