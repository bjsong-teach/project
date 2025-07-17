graph TD
    subgraph "사용자 영역"
        Client[💻 Client / Browser]
    end

    subgraph "게시판 서비스 (FastAPI)"
        style BoardService fill:#e6f7ff,stroke:#007bff
        BoardService[FastAPI Application]
    end

    subgraph "데이터 저장소"
        style DB fill:#e6f3e6,stroke:#28a745
        style Redis fill:#fff0f1,stroke:#dc3545
        DB["MySQL DB (SQLModel)"]
        Redis["⚡ Redis (조회수, 동기화 큐)"]
    end

    subgraph "외부 서비스"
        style UserService fill:#fff7e6,stroke:#ffc107
        UserService[👤 User Service]
    end
    
    subgraph "백그라운드 작업"
        style SyncWorker fill:#f0e6f7,stroke:#6f42c1
        SyncWorker[⚙️ Sync Worker]
    end

    Client -- API 요청 (HTTP) --> BoardService

    BoardService -- CRUD (게시글) --> DB
    BoardService -- 작성자 정보 조회 --> UserService
    
    BoardService -- "조회수 증가, 큐 추가/제거" --> Redis

    SyncWorker -. "1. 동기화 대상 확인" .-> Redis
    SyncWorker -. "2. DB에 조회수 업데이트" .-> DB
