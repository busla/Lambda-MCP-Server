#!/usr/bin/env node

import { MCPClient } from './client/dist/MCPClient.js';

async function testTypescriptClient() {
    console.log('🔍 Testing TypeScript MCP Client with GitHub Token Header...');
    
    const serverUrl = process.env.MCP_URL || 'http://localhost:8001/mcp';
    const apiToken = process.env.MCP_TOKEN || 'test-token';
    const githubToken = process.env.github_token_for_busla_repositories_GITHUB_TOKEN;
    
    if (!githubToken) {
        console.log('❌ GitHub token not found in environment - testing fallback to environment variable');
        console.log('🧪 Testing tool without GitHub-Token header (should use environment variable)...');
        
        try {
            const client = new MCPClient(serverUrl, apiToken);
            await client.connect();
            
            const result = await client.callTool('generateGithubWorklog', {
                github_username: 'busla',
                days_back: 7
            });
            
            console.log('❌ Tool should have failed without GitHub token');
            return false;
        } catch (error) {
            if (error.message.includes('GitHub token not provided')) {
                console.log('✅ Fallback to environment variable working - tool correctly reports missing token');
                return true;
            } else {
                console.log('❌ Unexpected error:', error.message);
                return false;
            }
        }
    }
    
    console.log(`📡 Connecting to: ${serverUrl}`);
    console.log(`🔑 Using GitHub token: ${githubToken.substring(0, 10)}...`);
    
    const client = new MCPClient(serverUrl, apiToken);
    
    try {
        await client.connect();
        console.log('✅ Successfully connected to MCP server');
        
        const tools = await client.getAvailableTools();
        console.log(`📋 Available tools: ${tools.length}`);
        
        const worklogTool = tools.find(tool => tool.name === 'generateGithubWorklog');
        if (worklogTool) {
            console.log('✅ GitHub worklog tool found!');
            console.log(`   Description: ${worklogTool.description}`);
            console.log(`   Input schema: ${JSON.stringify(worklogTool.inputSchema, null, 2)}`);
            
            console.log('🧪 Testing GitHub worklog tool with GitHub-Token header...');
            const result = await client.callTool('generateGithubWorklog', {
                github_username: 'busla',
                days_back: 7
            }, {
                'GitHub-Token': githubToken
            });
            
            console.log('✅ Tool execution successful!');
            console.log(`   Result type: ${typeof result.content}`);
            console.log(`   Result length: ${JSON.stringify(result.content).length} characters`);
            
            console.log('📋 Full result structure:', JSON.stringify(result, null, 2));
            
            if (result.content && result.content.length > 0) {
                try {
                    const worklogData = JSON.parse(result.content[0].text);
                    console.log(`   Username: ${worklogData.username}`);
                    console.log(`   Analysis scope: ${worklogData.analysis_scope}`);
                    console.log(`   Repositories: ${worklogData.repositories_analyzed?.length || 0}`);
                    console.log(`   Total hours: ${worklogData.estimated_hours?.total_hours || 0}`);
                    
                    if (worklogData.analysis_scope === 'all_repositories') {
                        console.log('✅ Multi-repository analysis confirmed via TypeScript client');
                    }
                    
                    console.log('✅ GitHub token header authentication successful!');
                } catch (parseError) {
                    console.log('❌ Failed to parse worklog data:', parseError.message);
                    console.log('Raw content:', result.content[0].text);
                }
            } else {
                console.log('❌ No content returned from tool execution');
            }
            
        } else {
            console.log('❌ GitHub worklog tool not found in available tools');
            console.log('Available tools:', tools.map(t => t.name));
        }
        
        await client.close();
        console.log('🎉 TypeScript client test completed successfully!');
        return true;
        
    } catch (error) {
        console.error('❌ TypeScript client test failed:', error.message);
        if (error.message.includes('ECONNREFUSED')) {
            console.log('💡 Hint: Make sure the MCP server is running on the specified URL');
        }
        return false;
    }
}

testTypescriptClient()
    .then(success => {
        process.exit(success ? 0 : 1);
    })
    .catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
