import { createFileRoute } from '@tanstack/react-router';
import YAMLConfigDetailPage from '../components/YAMLConfigDetailPage';

export const Route = createFileRoute('/yaml/$configId')({
  component: YAMLConfigDetailPage,
}); 