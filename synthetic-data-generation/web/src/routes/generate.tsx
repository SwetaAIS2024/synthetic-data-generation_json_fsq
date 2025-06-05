import { createFileRoute } from '@tanstack/react-router'
import YAMLGenerationPage from '../components/YAMLGenerationPage'

export const Route = createFileRoute('/generate')({
  component: YAMLGenerationPage,
}) 