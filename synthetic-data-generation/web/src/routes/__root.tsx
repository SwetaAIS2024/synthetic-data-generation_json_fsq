import * as React from 'react'
import { Link, Outlet, createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'

export const Route = createRootRoute({
  component: RootComponent,
})

function RootComponent() {
  return (
    <div className="min-h-screen bg-gradient-to-r from-gray-100 to-gray-200 p-8">
       <div className="max-w-6xl mx-auto mb-8 bg-white shadow-lg rounded-2xl">
        <div className="flex items-center bg-gradient-to-r from-indigo-500 to-purple-500 rounded-t-2xl p-6">
          <img
            src="/fireworks-ai-logo.png"
            alt="fireworks.ai Logo"
            className="w-25 rounded-lg mr-4"
          />
          <h2 className="text-3xl font-bold text-white">Synthetic Datasets using Knowledge Distillation</h2>
        </div>
      </div>
      <div className="max-w-6xl mx-auto bg-white shadow-lg rounded-2xl">
        <div className="flex border-b border-gray-200 bg-gray-50 rounded-t-2xl">
          
          <Link 
            to="/"
            className="px-6 py-2 cursor-pointer border-b-2 border-transparent hover:border-gray-400"
            activeProps={{
              className: "px-6 py-2 cursor-pointer border-b-2 border-indigo-500 font-medium"
            }}
          >
            Dashboard
          </Link>

          <Link 
            to="/generate"
            className="px-6 py-2 cursor-pointer border-b-2 border-transparent hover:border-gray-400"
            activeProps={{
              className: "px-6 py-2 cursor-pointer border-b-2 border-indigo-500 font-medium"
            }}
          >
            Generate YAML
          </Link>

        </div>
        <div className="p-6">
          <Outlet />
        </div>
      </div>
      <TanStackRouterDevtools position="bottom-right" />
    </div>
  )
}
