import type { EnhancedQueryResponse } from '@/types/api'
import './TimelineTab.css'

interface TimelineTabProps {
  response: EnhancedQueryResponse
}

export default function TimelineTab({ response }: TimelineTabProps) {
  const timeline = response.timeline

  return (
    <div className="timeline-tab">
      <h3>Execution Timeline</h3>
      <div className="timeline-container">
        {timeline.events.map((event, idx) => (
          <div key={idx} className="timeline-event">
            <div className="timeline-marker">
              <div className={`timeline-dot ${event.type}`} />
              {idx < timeline.events.length - 1 && <div className="timeline-line" />}
            </div>
            <div className="timeline-content">
              <div className="timeline-header">
                <span className={`event-type ${event.type}`}>
                  {event.type.replace('_', ' ')}
                </span>
                <span className="event-time">
                  {event.start_time_ms.toFixed(0)}ms
                </span>
              </div>
              {event.name && (
                <div className="event-agent">{event.name}</div>
              )}
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="event-description">Event details</div>
              )}
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <details className="event-metadata">
                  <summary>Metadata</summary>
                  <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
                </details>
              )}
              {event.duration_ms !== undefined && (
                <div className="event-duration">Duration: {event.duration_ms.toFixed(0)}ms</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
