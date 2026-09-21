"""
Worker package: background processes for async task execution.

Current workers:
  - outbox_worker: processes transactional outbox (email, webhooks, etc.)
  - (future: file scanner, cleanup jobs)
"""
