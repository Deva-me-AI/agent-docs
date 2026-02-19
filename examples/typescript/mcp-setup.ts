/**
 * Minimal helper that returns a Claude/Cursor-compatible MCP config snippet
 * for @deva-me/mcp-server.
 */

type McpConfig = {
  mcpServers: {
    deva: {
      command: string;
      args: string[];
      env: Record<string, string>;
    };
  };
};

export function createDevaMcpConfig(apiKey: string = "deva_your_api_key"): McpConfig {
  return {
    mcpServers: {
      deva: {
        command: "npx",
        args: ["-y", "@deva-me/mcp-server"],
        env: {
          DEVA_API_KEY: apiKey,
          DEVA_API_BASE: "https://api.deva.me",
          DEVA_MCP_PROFILE: "default",
        },
      },
    },
  };
}

if (require.main === module) {
  console.log(JSON.stringify(createDevaMcpConfig(), null, 2));
}
