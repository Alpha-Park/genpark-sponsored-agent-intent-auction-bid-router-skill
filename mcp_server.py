"""MCP JSON-RPC stdio server for genpark-sponsored-agent-intent-auction-bid-router-skill."""
import sys
import json
from client import SponsoredAgentIntentAuctionRouter

router = SponsoredAgentIntentAuctionRouter()

def handle_call_tool(params):
    name = params.get("name")
    args = params.get("arguments", {})
    if name != "route_sponsored_intent":
        return {"error": f"Unknown tool '{name}'"}
        
    action = args.get("action")
    if action == "register_sponsor_campaign":
        return router.register_sponsor_campaign(
            brand_name=args.get("brand_name", "BrandPartner"),
            target_keywords=args.get("target_keywords", []),
            bid_cpc_usd=float(args.get("bid_cpc_usd", 1.50))
        )
    elif action == "conduct_intent_auction":
        return router.conduct_intent_auction(
            query_text=args.get("query_text", "")
        )
    elif action == "format_sponsored_recommendation":
        return router.format_sponsored_recommendation(
            query=args.get("query_text", ""),
            organic_recommendation=args.get("organic_recommendation", "Standard organic product result.")
        )
    elif action == "record_conversion_attribution":
        return router.record_conversion_attribution(
            campaign_id=args.get("winning_campaign_id", ""),
            action_type=args.get("action_type", "CLICK")
        )
    else:
        return {"error": f"Unknown action '{action}'"}

def main():
    if "--test" in sys.argv:
        print("[TEST] Running self-test for SponsoredAgentIntentAuctionRouter...")
        router.register_sponsor_campaign("Instacart", ["groceries", "food delivery", "fresh produce"], bid_cpc_usd=2.50)
        router.register_sponsor_campaign("Walmart", ["groceries", "cheap household goods"], bid_cpc_usd=1.80)
        
        auc = router.conduct_intent_auction("Need weekly organic groceries delivered")
        assert auc["status"] == "success"
        assert auc["winner"]["brand"] == "Instacart"
        
        res = router.format_sponsored_recommendation("groceries", "Here are 3 local grocery options.")
        assert res["has_sponsored_placement"] is True
        print(f"[TEST] Success! Winner: {auc['winner']['brand']}, Clearing CPC: ${auc['clearing_price_usd']}")
        return

    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)
                continue
            if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}), flush=True)
                continue
            # JSON-RPC notifications never receive a response or execute request-only tools.
            if "id" not in req:
                continue
            if req["method"] == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {
                    "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": 'genpark-sponsored-agent-intent-auction-bid-router-skill', "version": "1.0.0"}
                }}), flush=True)
                continue
            if req["method"] == "ping":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {}}), flush=True)
                continue
            if req["method"] not in ("tools/list", "tools/call"):
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
                continue
            if req["method"] == "tools/call":
                params = req.get("params")
                if not isinstance(params, dict) or not isinstance(params.get("arguments", {}), dict) or params.get("name") not in ('route_sponsored_intent',):
                    print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32602, "message": "Unknown tool or invalid arguments"}}), flush=True)
                    continue
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "route_sponsored_intent",
                                "description": "Register sponsor campaigns, conduct second-price intent auctions, format transparent sponsored recommendations, and track conversion attribution.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string", "enum": ["register_sponsor_campaign", "conduct_intent_auction", "format_sponsored_recommendation", "record_conversion_attribution"]},
                                        "campaign_id": {"type": "string"},
                                        "brand_name": {"type": "string"},
                                        "bid_cpc_usd": {"type": "number"},
                                        "target_keywords": {"type": "array", "items": {"type": "string"}},
                                        "query_text": {"type": "string"},
                                        "winning_campaign_id": {"type": "string"}
                                    },
                                    "required": ["action"]
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                res = handle_call_tool(req.get("params", {}))
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
                }
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            print(json.dumps(resp), flush=True)
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None, "error": {"code": -32000, "message": str(e)}}
            print(json.dumps(err_resp), flush=True)

if __name__ == "__main__":
    main()
