import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface SubscriptionItem {
    merchant_name?: string;
    merchant_descriptor: string;
    amount_avg: number;
    frequency?: string;
    confidence_score?: number;
    recommendation?: string;
    is_subscription: boolean;
}

interface SubscriptionCardProps {
  item: SubscriptionItem;
}

export function SubscriptionCard({ item }: SubscriptionCardProps) {
  const confidenceColor = (item.confidence_score || 0) > 0.8 ? "bg-green-100 text-green-800" :
                          (item.confidence_score || 0) > 0.5 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";

  return (
    <Card className="w-full h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-3 overflow-hidden">
          <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center font-bold text-gray-500 text-sm">
            {(item.merchant_name?.[0] || item.merchant_descriptor[0]).toUpperCase()}
          </div>
          <div className="flex flex-col overflow-hidden">
             <span className="font-semibold truncate" title={item.merchant_name || item.merchant_descriptor}>
                {item.merchant_name || item.merchant_descriptor}
             </span>
             <span className="text-xs text-gray-500 capitalize">{item.frequency || "Unknown"}</span>
          </div>
        </div>
        <div className={`flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium ${confidenceColor}`}>
          {Math.round((item.confidence_score || 0) * 100)}%
        </div>
      </CardHeader>
      <CardContent className="flex-grow">
        <div className="text-2xl font-bold">€{item.amount_avg.toFixed(2)}</div>
        <p className="text-xs text-muted-foreground mt-2 line-clamp-3">
          {item.recommendation}
        </p>
      </CardContent>
      <CardFooter>
        <Button variant="outline" size="sm" className="w-full text-xs">
          View Details
        </Button>
      </CardFooter>
    </Card>
  )
}
