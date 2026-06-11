import { Button } from "@/shared/components/ui/button"

function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-foreground">
          AI Interview & Presentation Coach
        </h1>
        <p className="text-muted-foreground">
          Platform is being built...
        </p>
        <Button>Get Started</Button>
      </div>
    </div>
  )
}

export default App
