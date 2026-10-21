import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it("redirige vers /login et affiche la marque EduManage", () => {
    render(<App />)

    expect(screen.getByText('EduManage')).toBeInTheDocument()
  })
})
