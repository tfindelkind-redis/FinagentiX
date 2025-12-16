import { useState } from 'react'
import { ChevronDown, Lightbulb, Play, BookOpen, Zap, HelpCircle } from 'lucide-react'
import { 
  LEARN_MODE_QUESTIONS, 
  QUESTION_CATEGORIES,
  type LearnModeQuestion 
} from '@/data/learnModeQuestions'
import './LearnMode.css'

interface LearnModeProps {
  onSelectQuestion: (question: string) => void
  isDisabled?: boolean
}

export default function LearnMode({ onSelectQuestion, isDisabled }: LearnModeProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [hoveredQuestion, setHoveredQuestion] = useState<LearnModeQuestion | null>(null)

  const filteredQuestions = selectedCategory
    ? LEARN_MODE_QUESTIONS.filter(q => q.category === selectedCategory)
    : LEARN_MODE_QUESTIONS

  const handleQuestionClick = (question: LearnModeQuestion) => {
    if (!isDisabled) {
      onSelectQuestion(question.question)
    }
  }

  return (
    <div className={`learn-mode ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <button 
        className="learn-mode-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="learn-mode-title">
          <Lightbulb className="learn-icon" size={20} />
          <span>Learn Mode</span>
          <span className="learn-badge">Showcase Redis AI</span>
        </div>
        <ChevronDown className={`chevron ${isExpanded ? 'rotated' : ''}`} size={20} />
      </button>

      {isExpanded && (
        <div className="learn-mode-content">
          <p className="learn-description">
            <BookOpen size={16} />
            Select a pre-built question to see how Redis accelerates AI agents. 
            Each question showcases different agents and Redis patterns.
          </p>

          {/* Category Filter */}
          <div className="category-filter">
            <button
              className={`category-btn ${selectedCategory === null ? 'active' : ''}`}
              onClick={() => setSelectedCategory(null)}
            >
              All
            </button>
            {Object.entries(QUESTION_CATEGORIES).map(([key, cat]) => (
              <button
                key={key}
                className={`category-btn ${selectedCategory === key ? 'active' : ''}`}
                onClick={() => setSelectedCategory(key)}
                style={{ '--category-color': cat.color } as React.CSSProperties}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Question List */}
          <div className="question-list">
            {filteredQuestions.map((q) => (
              <div
                key={q.id}
                className={`question-item ${isDisabled ? 'disabled' : ''} ${q.id.includes('cache-demo') ? 'featured' : ''}`}
                onMouseEnter={() => setHoveredQuestion(q)}
                onMouseLeave={() => setHoveredQuestion(null)}
                onClick={() => handleQuestionClick(q)}
              >
                <div className="question-main">
                  <span 
                    className="question-category-dot"
                    style={{ backgroundColor: QUESTION_CATEGORIES[q.category].color }}
                  />
                  <span className="question-text">{q.question}</span>
                  <Play className="play-icon" size={16} />
                </div>

                {/* Hover Details */}
                {hoveredQuestion?.id === q.id && (
                  <div className="question-details">
                    <p className="question-description">{q.description}</p>
                    
                    <div className="question-meta">
                      <div className="meta-section">
                        <span className="meta-label">
                          <Zap size={12} /> Agents:
                        </span>
                        <div className="meta-tags">
                          {q.agentsInvolved.map((agent, idx) => (
                            <span key={idx} className="agent-tag">{agent}</span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="meta-section">
                        <span className="meta-label">
                          <HelpCircle size={12} /> Redis Patterns:
                        </span>
                        <div className="meta-tags">
                          {q.redisPatterns.map((pattern, idx) => (
                            <span key={idx} className="redis-tag">{pattern}</span>
                          ))}
                        </div>
                      </div>

                      <div className="meta-section benefits">
                        <span className="meta-label">Expected Benefits:</span>
                        <ul className="benefits-list">
                          {q.expectedBenefits.map((benefit, idx) => (
                            <li key={idx}>{benefit}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="difficulty-badge" data-difficulty={q.difficulty}>
                      {q.difficulty}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Quick Tips */}
          <div className="learn-tips">
            <h4>💡 Pro Tips</h4>
            <ul>
              <li><strong>Cache Demo:</strong> Ask the same question twice to see 137x faster response!</li>
              <li><strong>Semantic Match:</strong> Try rephrasing ("AAPL price" vs "Apple stock price")</li>
              <li><strong>Watch Timeline:</strong> See each Redis pattern in action</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
