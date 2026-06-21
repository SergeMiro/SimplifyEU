import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import React from "react";

interface SocialButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  provider: "google";
}

export function SocialButton({ className, icon, provider, ...props }: SocialButtonProps) {
  return (
    <Button
      variant="outline"
      size="icon"
      type="button"
      className={cn(
        "rounded-full w-12 h-12 border-muted-foreground/20 hover:bg-muted/50 transition-all duration-200 shadow-sm",
        className
      )}
      {...props}
    >
      {icon}
      <span className="sr-only">Sign in with {provider}</span>
    </Button>
  );
}
