import * as React from 'react';
import { createFileRoute } from '@tanstack/react-router';
import YAMLConfigDashboard from '../components/YAMLConfigDashboard';
export const Route = createFileRoute('/')({
  component: DashboardComponent,
});

function DashboardComponent() {
  return (
    <div>
      <YAMLConfigDashboard />
    </div>
  );
}

export default DashboardComponent;