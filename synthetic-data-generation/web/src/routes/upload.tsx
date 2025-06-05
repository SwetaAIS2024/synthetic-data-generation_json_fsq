import * as React from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect } from 'react';

export const Route = createFileRoute('/upload')({
  component: UploadRedirect,
});

function UploadRedirect() {
  const navigate = useNavigate();
  
  useEffect(() => {
    // Redirect to dashboard
    navigate({ to: '/' });
  }, [navigate]);

  return null;
}

export default UploadRedirect;
