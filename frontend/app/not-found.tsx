import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CompassIcon } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-12">
      <Card className="w-full max-w-sm text-center">
        <CardHeader>
          <CardTitle className="flex items-center justify-center gap-2">
            <CompassIcon className="h-5 w-5" />
            Not found
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            That page - or that game - doesn&apos;t exist.
          </p>
          <Button asChild>
            <Link href="/">Start a new game</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
