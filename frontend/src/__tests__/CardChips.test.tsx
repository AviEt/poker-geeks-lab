import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { CardChips } from '../components/CardChips'

describe('CardChips', () => {
  it('renders one chip per card in a cards string', () => {
    render(<CardChips cards="As Kh" />)
    expect(screen.getByText('A♠')).toBeDefined()
    expect(screen.getByText('K♥')).toBeDefined()
  })

  it('renders three chips for a flop string', () => {
    render(<CardChips cards="Ts 9d 2c" />)
    expect(screen.getByText('T♠')).toBeDefined()
    expect(screen.getByText('9♦')).toBeDefined()
    expect(screen.getByText('2♣')).toBeDefined()
  })

  it('applies suit--spade class to spade cards', () => {
    const { container } = render(<CardChips cards="As" />)
    expect(container.querySelector('.suit--spade')).not.toBeNull()
  })

  it('applies suit--heart class to heart cards', () => {
    const { container } = render(<CardChips cards="Kh" />)
    expect(container.querySelector('.suit--heart')).not.toBeNull()
  })

  it('applies suit--diamond class to diamond cards', () => {
    const { container } = render(<CardChips cards="Qd" />)
    expect(container.querySelector('.suit--diamond')).not.toBeNull()
  })

  it('applies suit--club class to club cards', () => {
    const { container } = render(<CardChips cards="Jc" />)
    expect(container.querySelector('.suit--club')).not.toBeNull()
  })

  it('renders a dash for null cards', () => {
    render(<CardChips cards={null} />)
    expect(screen.getByText('—')).toBeDefined()
  })

  it('renders a dash for empty string', () => {
    render(<CardChips cards="" />)
    expect(screen.getByText('—')).toBeDefined()
  })
})
