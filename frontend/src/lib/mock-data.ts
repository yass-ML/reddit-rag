import type {
  ChatThread,
  IngestionRun,
  NormalizedComment,
  NormalizedPost,
  QueryTemplate,
  QueryThemeInsight,
  RagAnswer,
  RagQuestion,
  ResearchWorkspace,
  SourceEvidence,
  SubredditConfig,
} from "@/lib/contracts";

export const workspaces: ResearchWorkspace[] = [
  {
    id: "ws-founder-research",
    name: "Founder Pain Point Research",
    goal: "Understand recurring objections, language, and buying triggers from indie founder communities.",
    created_at: "2026-04-20T08:30:00Z",
    updated_at: "2026-04-25T09:12:00Z",
    status: "mocked",
    subreddit_ids: ["sr-startups", "sr-saas", "sr-entrepreneur"],
    recent_question_ids: ["q-001", "q-002"],
    stats: {
      posts: 248,
      comments: 1934,
      chunks: 612,
      sources_ready: 42,
    },
  },
  {
    id: "ws-local-ai",
    name: "Local AI Workflow Research",
    goal: "Map what local-first AI users value when choosing tooling and model workflows.",
    created_at: "2026-04-22T11:04:00Z",
    updated_at: "2026-04-24T16:44:00Z",
    status: "ready",
    subreddit_ids: ["sr-localllama", "sr-selfhosted"],
    recent_question_ids: ["q-003"],
    stats: {
      posts: 132,
      comments: 870,
      chunks: 319,
      sources_ready: 28,
    },
  },
];

export const subredditConfigs: SubredditConfig[] = [
  {
    id: "sr-startups",
    workspace_id: "ws-founder-research",
    name: "startups",
    description: "Early-stage startup discussion and founder advice.",
    post_limit: 100,
    comment_depth: 4,
    timeframe: "month",
    status: "mocked",
    last_ingested_at: "2026-04-25T08:40:00Z",
  },
  {
    id: "sr-saas",
    workspace_id: "ws-founder-research",
    name: "SaaS",
    description: "SaaS building, pricing, onboarding, and customer acquisition.",
    post_limit: 80,
    comment_depth: 3,
    timeframe: "month",
    status: "processing",
    last_ingested_at: "2026-04-25T08:52:00Z",
  },
  {
    id: "sr-entrepreneur",
    workspace_id: "ws-founder-research",
    name: "Entrepreneur",
    description: "Broad entrepreneurship questions and tactical advice.",
    post_limit: 75,
    comment_depth: 3,
    timeframe: "month",
    status: "queued",
    last_ingested_at: null,
  },
  {
    id: "sr-localllama",
    workspace_id: "ws-local-ai",
    name: "LocalLLaMA",
    description: "Local LLM experiments, quantization, and deployment notes.",
    post_limit: 120,
    comment_depth: 4,
    timeframe: "week",
    status: "ready",
    last_ingested_at: "2026-04-24T16:41:00Z",
  },
  {
    id: "sr-selfhosted",
    workspace_id: "ws-local-ai",
    name: "selfhosted",
    description: "Self-hosted services and local infrastructure patterns.",
    post_limit: 90,
    comment_depth: 3,
    timeframe: "week",
    status: "ready",
    last_ingested_at: "2026-04-24T16:42:00Z",
  },
];

export const normalizedPosts: NormalizedPost[] = [
  {
    id: "post-001",
    reddit_id: "abc123",
    subreddit: "SaaS",
    title: "What finally made you pay for a founder tool?",
    body: "I keep trying tools that look useful, but I only pay when they save a weekly ritual or make customer calls easier to synthesize.",
    author: "bootstrapped_builder",
    score: 184,
    num_comments: 67,
    created_utc: "2026-04-21T14:15:00Z",
    permalink: "https://reddit.example/r/SaaS/comments/abc123",
    url: null,
    raw_path: "data/raw/SaaS/abc123.json",
  },
  {
    id: "post-002",
    reddit_id: "def456",
    subreddit: "startups",
    title: "How do you validate a pain point without spamming people?",
    body: "The advice is always talk to customers, but getting honest signals without pitching is hard.",
    author: "signal_seeker",
    score: 219,
    num_comments: 102,
    created_utc: "2026-04-22T09:02:00Z",
    permalink: "https://reddit.example/r/startups/comments/def456",
    url: null,
    raw_path: "data/raw/startups/def456.json",
  },
];

export const normalizedComments: NormalizedComment[] = [
  {
    id: "comment-001",
    reddit_id: "cmt789",
    post_reddit_id: "abc123",
    parent_reddit_id: "abc123",
    subreddit: "SaaS",
    body: "The moment of value is usually when a tool turns messy qualitative notes into a next decision. If it only stores notes, I churn.",
    author: "research_ops",
    score: 92,
    created_utc: "2026-04-21T15:03:00Z",
    permalink: "https://reddit.example/r/SaaS/comments/abc123/cmt789",
    raw_path: "data/raw/SaaS/cmt789.json",
  },
  {
    id: "comment-002",
    reddit_id: "cmt101",
    post_reddit_id: "def456",
    parent_reddit_id: "def456",
    subreddit: "startups",
    body: "Ask people to rank recent annoyances. You get better language when they describe the workaround they already built.",
    author: "customer_calls",
    score: 71,
    created_utc: "2026-04-22T10:11:00Z",
    permalink: "https://reddit.example/r/startups/comments/def456/cmt101",
    raw_path: "data/raw/startups/cmt101.json",
  },
];

export const sources: SourceEvidence[] = [
  {
    id: "src-001",
    chunk_id: "chunk-001",
    source_id: "comment-001",
    source_type: "comment",
    subreddit: "SaaS",
    text: "The moment of value is usually when a tool turns messy qualitative notes into a next decision. If it only stores notes, I churn.",
    score: 0.91,
    metadata: {
      reddit_id: "cmt789",
      post_reddit_id: "abc123",
      title: "What finally made you pay for a founder tool?",
      permalink: "https://reddit.example/r/SaaS/comments/abc123/cmt789",
      score: 92,
      created_utc: "2026-04-21T15:03:00Z",
      chunk_index: 0,
    },
    source_permalink: "https://reddit.example/r/SaaS/comments/abc123/cmt789",
    source_title: "What finally made you pay for a founder tool?",
    author: "research_ops",
    source_score: 92,
    excerpt:
      "A tool becomes worth paying for when it turns messy qualitative notes into a next decision.",
    local_raw_path: "data/raw/SaaS/cmt789.json",
  },
  {
    id: "src-002",
    chunk_id: "chunk-002",
    source_id: "post-002",
    source_type: "post",
    subreddit: "startups",
    text: "The advice is always talk to customers, but getting honest signals without pitching is hard.",
    score: 0.87,
    metadata: {
      reddit_id: "def456",
      post_reddit_id: "def456",
      title: "How do you validate a pain point without spamming people?",
      permalink: "https://reddit.example/r/startups/comments/def456",
      score: 219,
      created_utc: "2026-04-22T09:02:00Z",
      chunk_index: 1,
    },
    source_permalink: "https://reddit.example/r/startups/comments/def456",
    source_title: "How do you validate a pain point without spamming people?",
    author: "signal_seeker",
    source_score: 219,
    comment_count: 102,
    excerpt:
      "Founders want honest customer signals, but they worry that direct outreach turns into pitching.",
    local_raw_path: "data/raw/startups/def456.json",
  },
  {
    id: "src-003",
    chunk_id: "chunk-003",
    source_id: "comment-002",
    source_type: "comment",
    subreddit: "startups",
    text: "Ask people to rank recent annoyances. You get better language when they describe the workaround they already built.",
    score: 0.84,
    metadata: {
      reddit_id: "cmt101",
      post_reddit_id: "def456",
      title: "How do you validate a pain point without spamming people?",
      permalink: "https://reddit.example/r/startups/comments/def456/cmt101",
      score: 71,
      created_utc: "2026-04-22T10:11:00Z",
      chunk_index: 0,
    },
    source_permalink: "https://reddit.example/r/startups/comments/def456/cmt101",
    source_title: "How do you validate a pain point without spamming people?",
    author: "customer_calls",
    source_score: 71,
    excerpt:
      "Workarounds reveal the user's own vocabulary and the severity of the pain point.",
    local_raw_path: "data/raw/startups/cmt101.json",
  },
];

export const answers: RagAnswer[] = [
  {
    id: "ans-001",
    question: "What language do founders use when they describe valuable research tools?",
    answer_text:
      "Founders describe value in decision-oriented language: saving weekly rituals, turning messy notes into the next decision, and revealing workarounds that prove the pain is active. The strongest buying signal is not storage or summarization alone, but whether the tool helps them move from scattered customer evidence to a concrete action.",
    sources,
    retrieval_debug_optional: {
      retrieval_ms: 42,
      embedding_model: "mock-ollama-embed",
      generation_model: "mock-local-llm",
      top_k: 3,
      mocked: true,
    },
  },
];

export const questions: RagQuestion[] = [
  {
    id: "q-001",
    workspace_id: "ws-founder-research",
    question: answers[0].question,
    created_at: "2026-04-25T09:10:00Z",
    answer_id: "ans-001",
  },
  {
    id: "q-002",
    workspace_id: "ws-founder-research",
    question: "What objections repeat before someone tries a SaaS research tool?",
    created_at: "2026-04-24T18:20:00Z",
    answer_id: "ans-001",
  },
  {
    id: "q-003",
    workspace_id: "ws-local-ai",
    question: "What do local LLM users say makes a workflow feel private?",
    created_at: "2026-04-24T16:50:00Z",
    answer_id: "ans-001",
  },
];

export const queryTemplates: QueryTemplate[] = [
  {
    id: "tmpl-themes",
    title: "Find recurring themes",
    category: "themes",
    prompt:
      "What themes appear repeatedly across these subreddit discussions, and which sources best support each theme?",
  },
  {
    id: "tmpl-pain",
    title: "Surface pain points",
    category: "pain_points",
    prompt:
      "What pain points are users describing in their own words, and what workarounds prove the pain is real?",
  },
  {
    id: "tmpl-vocab",
    title: "Extract user vocabulary",
    category: "vocabulary",
    prompt:
      "What phrases, metaphors, and labels do users use when describing this problem space?",
  },
  {
    id: "tmpl-objections",
    title: "Map objections",
    category: "objections",
    prompt:
      "What objections or trust concerns appear before users adopt a tool in this category?",
  },
];

export const queryThemeInsights: QueryThemeInsight[] = [
  {
    id: "theme-decision",
    title: "Decision support beats note storage",
    summary:
      "Founders frame value around moving from messy evidence to the next action, not around keeping a prettier archive.",
    source_ids: ["src-001", "src-002"],
    confidence: "high",
  },
  {
    id: "theme-workarounds",
    title: "Workarounds reveal active pain",
    summary:
      "The most useful language appears when users describe what they already hacked together to solve the problem.",
    source_ids: ["src-002", "src-003"],
    confidence: "high",
  },
  {
    id: "theme-trust",
    title: "Honest signal is fragile",
    summary:
      "Users worry that research outreach can become a pitch, so neutral question framing matters.",
    source_ids: ["src-002"],
    confidence: "medium",
  },
];

export const chatThread: ChatThread = {
  id: "thread-founder-value-language",
  workspace_id: "ws-founder-research",
  title: "Founder value language",
  messages: [
    {
      id: "msg-system-001",
      role: "system",
      content:
        "Mock chat mode is using local fixtures only. Future responses will come from the local RAG API with inspectable citations.",
      created_at: "2026-04-25T09:08:00Z",
    },
    {
      id: "msg-user-001",
      role: "user",
      content:
        "What language do founders use when they describe valuable research tools?",
      created_at: "2026-04-25T09:10:00Z",
    },
    {
      id: "msg-assistant-001",
      role: "assistant",
      content:
        "They describe value in decision-oriented language: saving a weekly ritual, turning messy notes into the next decision, and revealing workarounds that prove the pain is active. The clearest buying signal is not storage by itself, but whether the tool helps move from scattered customer evidence to a concrete action.",
      created_at: "2026-04-25T09:10:12Z",
      citation_source_ids: ["src-001", "src-002", "src-003"],
    },
    {
      id: "msg-user-002",
      role: "user",
      content: "What follow-up should I ask to validate this more deeply?",
      created_at: "2026-04-25T09:11:00Z",
    },
    {
      id: "msg-assistant-002",
      role: "assistant",
      content:
        "Ask for examples of the last time they manually synthesized customer notes and what decision came out of it. That should uncover the workflow, the language they use for the pain, and whether they already have a workaround worth replacing.",
      created_at: "2026-04-25T09:11:08Z",
      citation_source_ids: ["src-001", "src-003"],
    },
  ],
};

export const ingestionRun: IngestionRun = {
  id: "ing-001",
  workspace_id: "ws-founder-research",
  started_at: "2026-04-25T08:40:00Z",
  finished_at: null,
  status: "mocked",
  progress: 68,
  steps: [
    {
      id: "step-config",
      label: "Workspace configured",
      description: "Subreddit targets and local limits are saved.",
      status: "ready",
      count: 3,
    },
    {
      id: "step-fetch",
      label: "Reddit API fetch",
      description: "Mocked until the Python ingestion worker is implemented.",
      status: "mocked",
      count: 248,
    },
    {
      id: "step-normalize",
      label: "Normalize records",
      description: "Contract preview for posts, comments, and source metadata.",
      status: "processing",
      count: 2182,
    },
    {
      id: "step-embed",
      label: "Embed chunks",
      description: "Pending future local embedding model integration.",
      status: "queued",
      count: 612,
    },
  ],
  subreddit_statuses: [
    {
      subreddit: "startups",
      status: "ready",
      posts_seen: 96,
      comments_seen: 834,
      chunks_ready: 224,
      message: "Mock records are ready for querying.",
    },
    {
      subreddit: "SaaS",
      status: "processing",
      posts_seen: 88,
      comments_seen: 720,
      chunks_ready: 238,
      message: "Normalizing comments into source chunks.",
    },
    {
      subreddit: "Entrepreneur",
      status: "queued",
      posts_seen: 64,
      comments_seen: 380,
      chunks_ready: 150,
      message: "Queued for future ingestion worker.",
    },
  ],
};
