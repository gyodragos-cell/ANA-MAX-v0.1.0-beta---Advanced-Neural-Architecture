# ANA MAX Dashboard Backend

## API Endpoints

- `/health`: runtime and cluster health.
- `/events`: observability event stream.
- `/tools`: tool catalog and capability map.
- `/memory`: semantic and episodic memory summary.
- `/agents`: agent/process table.
- `/nodes`: distributed node metrics.

## Event Streams

Events should include category, timestamp, source, safe payload, and correlation
ID. Private reasoning content must not be streamed.

## Node Metrics

- node role
- health
- load
- failure count
- latency

## Memory View

Show counts, tags, and safe summaries only. Do not expose private memory values
without explicit operator approval.

## Agent View

Show role, state, current task, and recent safe events.
