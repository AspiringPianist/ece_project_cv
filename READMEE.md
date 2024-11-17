```mermaid
graph TD
    A[Input Audio in Kannada] --> B[Task 1: Speech Recognition (ASR Model)]
    B --> C[ASR Output: Transcribed Text in Kannada]

    C --> D[Translation API - Translate Text to English]
    D --> E[Store Translated Text in Vector DB for RAG]

    subgraph Task 2: Speech-based Question Answering
        G[User Question in Speech] --> H[Speech to Text Translate API]
        H --> I[Question Translated to English Text]
        I --> J[Retrieve Relevant Segment from Vector DB using RAG]
        J --> K[Return Relevant Answer Segment in Text]
        K --> L[Optional: Translate Answer Text to Kannada]
    end

    E --> J
```