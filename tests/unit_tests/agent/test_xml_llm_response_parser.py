import pytest
from autobyteus.agent.xml_llm_response_parser import XMLLLMResponseParser
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser():
    return XMLLLMResponseParser()

def test_parse_valid_response(parser):
    response = '''
    I am currently in my reasoning phase, strategizing the best course of action to complete this task.
    To recommend an encouraging movie for students, I should first find out what movies are popular in this category.
    <command name="SearchTool">
        <arg name="query">encouraging movies for students</arg>
    </command>
    I will stop here now and wait for the SearchTool to return the results...
    '''
    expected_tool_invocation = ToolInvocation(
        name="SearchTool",
        arguments={"query": "encouraging movies for students"}
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments


def test_parse_web_element_trigger_command(parser):
    response = '''
    <command name="SendMessageTo">
  <arg name="recipient_role_name">CoordinationAgent</arg>
  <arg name="recipient_agent_id">CoordinationAgent-001</arg>
  <arg name="content">

**Summary of the Product Details:**

- **Product Name:** Starting a Business in Berlin
- **Price:** EUR 26.00 for each sole trade, EUR 31.00 for legal entities with one representative, EUR 13.00 for additional representatives of legal entities, and EUR 15.00 for electronic procedures.
- **Key Features:** Business registration services including trade registration, permit applications, notifications, and tax registrations.

**Detailed Product Specifications:**

1. **Business Registration:**
   - Required for new independent businesses with a permanent place of business in Berlin.
   - Costs:
     - EUR 26.00 per sole trader or partnership member.
     - EUR 31.00 for legal entities with one representative.
     - EUR 13.00 for each additional representative of a legal entity.
     - EUR 15.00 for electronic procedures.

2. **Permit Applications:**
   - Gastronomic trade permits available.
   - Insurance industry licensing requirements detailed.

3. **Notifications:**
   - Displaying itinerant camps requires notification.

4. **Tax Registrations:**
   - Mandatory even if no business registration is required (e.g., freelancers).
   - Can be submitted online via ELSTER portal or in writing to local tax offices.

5. **Additional Services:**
   - Entry in the Register of Crafts and recognition as test engineers available.
   - Special use permits to use public space necessary for certain activities like operating food trucks/mobile cafes.

**Pricing Information:**

- The costs associated with starting a business include:
    * Business registration fees ranging from EUR 26 to EUR 31 depending on the type of business entity.
    * Additional fees such as EUR 15 for electronic procedures.

**Customer Ratings and Reviews Summary:**

- No specific customer ratings or reviews were found on this webpage; however, it provides comprehensive information and links to various services related to starting a business in Berlin.

**Unique Selling Points:**

- The Point of Single Contact Berlin offers streamlined online services for registering trades, applying for permits, submitting notifications, and handling tax registrations efficiently.
- Detailed FAQs section addressing common questions about business registrations and related processes.

**Compatibility with User Requirements:**

- The webpage caters specifically to entrepreneurs looking to start or manage businesses in Berlin by providing detailed information on necessary steps and costs involved.

**Additional Insights Relevant for Product Recommendations:**

- The website is user-friendly with clear navigation through different sections related to starting up a business in Berlin.
- It includes links to other relevant resources such as tax offices' websites which can be useful for entrepreneurs needing further assistance beyond initial registration processes.

</content>
<arg name="message_type">TASK_RESULT</arg>
<arg name="sender_agent_id">page_reader_agent-001</arg>
</command>
    '''
    expected_tool_invocation = ToolInvocation(
        name="SearchTool",
        arguments={"query": "encouraging movies for students"}
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments


def test_parse_special_characters_response(parser):
    response = '''
   
**[Homeoffice-Pauschale wird verbessert - Bundesregierung.de](https://www.bundesregierung.de/breg-de/schwerpunkte/entlastung-fuer-deutschland/homeoffice-2125028)**\n   - This article from the German Federal Government explains that employees working from home can claim up to 1,000 Euros per year in their tax returns.\n\n2. **[Tax tip: Home office flat rate and office hours - KPMG](https://kpmg.com/de/en/home/insights/2024/06/tax-tip-home-office-lump-sum-and-office-hours.html)**\n   - KPMG provides insights into how the home office lump sum can be recognized for tax purposes, clarifying recent changes and guidelines.\n\n3. **[Your guide to tax deductions in Germany for 2023 - N26](https://n26.com/en-de/blog/guide-to-tax-deductions)**\n   - N26 offers a comprehensive guide on various tax deductions available in Germany, including the home office lump sum of €1,230 for work-related expenses.\n\n4. **[Study & Home Office: What Can I Deduct From Tax? - Taxfix](https://taxfix.de/en/home-office-and-study-deductions/)**\n   - Taxfix explains how individuals can deduct home office expenses as income-related expenses (Werbungskosten), with a daily allowance of up to 6 Euros.\n\n5. **[Germany - Individual - Deductions - PwC](https://taxsummaries.pwc.com/germany/individual/deductions)**\n   - PwC provides detailed information on individual income tax deductions in Germany, including special expense deductions like the home office lump sum.\n\nThese sources cover recent changes and provide detailed information on how Finanzamt calculates tax deductions for HomeOffice Pauschale in Germany.\n\n<command name="SendMessageTo">\n  <arg name="recipient_role_name">CoordinationAgent</arg>\n  <arg name="recipient_agent_id">CoordinationAgent-001</arg>\n  <arg name="content">Here are the most relevant URLs with brief summaries:\n\n1. [Homeoffice-Pauschale wird verbessert - Bundesregierung.de](https://www.bundesregierung.de/breg-de/schwerpunkte/entlastung-fuer-deutschland/homeoffice-2125028)\n   - This article from the German Federal Government explains that employees working from home can claim up to 1,000 Euros per year in their tax returns.\n\n2. [Tax tip: Home office flat rate and office hours - KPMG](https://kpmg.com/de/en/home/insights/2024/06/tax-tip-home-office-lump-sum-and-office-hours.html)\n   - KPMG provides insights into how the home office lump sum can be recognized for tax purposes, clarifying recent changes and guidelines.\n\n3. [Your guide to tax deductions in Germany for 2023 - N26](https://n26.com/en-de/blog/guide-to-tax-deductions)\n   - N26 offers a comprehensive guide on various tax deductions available in Germany, including the home office lump sum of €1,230 for work-related expenses.\n\n4. [Study & Home Office: What Can I Deduct From Tax? - Taxfix](https://taxfix.de/en/home-office-and-study-deductions/)\n   - Taxfix explains how individuals can deduct home office expenses as income-related expenses (Werbungskosten), with a daily allowance of up to 6 Euros.\n\n5. [Germany - Individual - Deductions - PwC](https://taxsummaries.pwc.com/germany/individual/deductions)\n   - PwC provides detailed information on individual income tax deductions in Germany, including special expense deductions like the home office lump sum.\n\nThese sources cover recent changes and provide detailed information on how Finanzamt calculates tax deductions for HomeOffice Pauschale in Germany.\n</arg>\n<arg name="message_type">TASK_RESULT</arg>\n<arg name="sender_agent_id">GoogleSearchAgent-001</arg>\n</command>',)
    '''
    expected_tool_invocation = ToolInvocation(
        name="SendMessageTo",
        arguments={
            "recipient_role_name": "CoordinationAgent",
            "recipient_agent_id": "CoordinationAgent-001",
            "content": "Here are the most relevant URLs with brief summaries:\n\n1. [Homeoffice-Pauschale wird verbessert - Bundesregierung.de](https://www.bundesregierung.de/breg-de/schwerpunkte/entlastung-fuer-deutschland/homeoffice-2125028)\n   - This article from the German Federal Government explains that employees working from home can claim up to 1,000 Euros per year in their tax returns.\n\n2. [Tax tip: Home office flat rate and office hours - KPMG](https://kpmg.com/de/en/home/insights/2024/06/tax-tip-home-office-lump-sum-and-office-hours.html)\n   - KPMG provides insights into how the home office lump sum can be recognized for tax purposes, clarifying recent changes and guidelines.\n\n3. [Your guide to tax deductions in Germany for 2023 - N26](https://n26.com/en-de/blog/guide-to-tax-deductions)\n   - N26 offers a comprehensive guide on various tax deductions available in Germany, including the home office lump sum of €1,230 for work-related expenses.\n\n4. [Study & Home Office: What Can I Deduct From Tax? - Taxfix](https://taxfix.de/en/home-office-and-study-deductions/)\n   - Taxfix explains how individuals can deduct home office expenses as income-related expenses (Werbungskosten), with a daily allowance of up to 6 Euros.\n\n5. [Germany - Individual - Deductions - PwC](https://taxsummaries.pwc.com/germany/individual/deductions)\n   - PwC provides detailed information on individual income tax deductions in Germany, including special expense deductions like the home office lump sum.\n\nThese sources cover recent changes and provide detailed information on how Finanzamt calculates tax deductions for HomeOffice Pauschale in Germany.",
            "message_type": "TASK_RESULT",
            "sender_agent_id": "GoogleSearchAgent-001"
        }
    )
    
    parsed_response = parser.parse_response(response)
    print(f"Parsed response: {parsed_response}")
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments



def test_parse_send_messageto_response(parser):
    response = '''

THINK: I need to send the screenshot to the ImageUnderstandingAgent to confirm successful navigation and identify key elements for the search.

ACT:
```xml
<command name="SendMessageTo">
  <arg name="recipient_role_name">ImageUnderstandingAgent</arg>
  <arg name="recipient_agent_id">unknown</arg>
  <arg name="content">
    <task_details>
      <task>Analyze the screenshot to confirm we've successfully navigated to the PubMed homepage</task>
      <purpose>To verify navigation and identify key elements for search</purpose>
      <context>
        <overall_goal>Search for a paper based on user's criteria, select one, and download its PDF</overall_goal>
        <current_stage>Confirming navigation to PubMed homepage</current_stage>
        <previous_actions>Attempted navigation to PubMed homepage and took a screenshot</previous_actions>
        <next_task>Confirm successful navigation and identify search box</next_task>
      </context>
    </task_details>
    Screenshot path: /home/ryan-ai/miniHDD/Learning/chatgpt/agents/pubmed_homepage.png
  </arg>
  <arg name="message_type">TASK_ASSIGNMENT</arg>
  <arg name="sender_agent_id">WebNavigationAgent-001</arg>
</command>
```

WAITING: Waiting for ImageUnderstandingAgent response...
    '''
    expected_tool_invocation = ToolInvocation(
        name="SendMessageTo",
        arguments={
            "recipient_role_name": "CoordinationAgent",
            "recipient_agent_id": "CoordinationAgent-001",
            "content": "Here are the most relevant URLs with brief summaries:\n\n1. [Homeoffice-Pauschale wird verbessert - Bundesregierung.de](https://www.bundesregierung.de/breg-de/schwerpunkte/entlastung-fuer-deutschland/homeoffice-2125028)\n   - This article from the German Federal Government explains that employees working from home can claim up to 1,000 Euros per year in their tax returns.\n\n2. [Tax tip: Home office flat rate and office hours - KPMG](https://kpmg.com/de/en/home/insights/2024/06/tax-tip-home-office-lump-sum-and-office-hours.html)\n   - KPMG provides insights into how the home office lump sum can be recognized for tax purposes, clarifying recent changes and guidelines.\n\n3. [Your guide to tax deductions in Germany for 2023 - N26](https://n26.com/en-de/blog/guide-to-tax-deductions)\n   - N26 offers a comprehensive guide on various tax deductions available in Germany, including the home office lump sum of €1,230 for work-related expenses.\n\n4. [Study & Home Office: What Can I Deduct From Tax? - Taxfix](https://taxfix.de/en/home-office-and-study-deductions/)\n   - Taxfix explains how individuals can deduct home office expenses as income-related expenses (Werbungskosten), with a daily allowance of up to 6 Euros.\n\n5. [Germany - Individual - Deductions - PwC](https://taxsummaries.pwc.com/germany/individual/deductions)\n   - PwC provides detailed information on individual income tax deductions in Germany, including special expense deductions like the home office lump sum.\n\nThese sources cover recent changes and provide detailed information on how Finanzamt calculates tax deductions for HomeOffice Pauschale in Germany.",
            "message_type": "TASK_RESULT",
            "sender_agent_id": "GoogleSearchAgent-001"
        }
    )
    
    parsed_response = parser.parse_response(response)
    print(f"Parsed response: {parsed_response}")
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments


def test_parse_response_without_command(parser):
    response = '''
    I am currently in my reasoning phase, strategizing the best course of action to complete this task.
    To recommend an encouraging movie for students, I should first find out what movies are popular in this category.
    I will stop here now and wait for the SearchTool to return the results...
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None

def test_parse_invalid_xml(parser):
    response = '''
    I am currently in my reasoning phase, strategizing the best course of action to complete this task.
    To recommend an encouraging movie for students, I should first find out what movies are popular in this category.
    <command name="SearchTool>
        <arg name="query">encouraging movies for students</arg>
    </command>
    I will stop here now and wait for the SearchTool to return the results...
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None

def test_parse_complex_xml_structure(parser):
    response = '''
    I have completed my search and found the following information:
    <command name="SendMessageTo">
        <arg name="to_role">CoordinationAgent</arg>
        <arg name="message">
            <list>
                <item>
                    <url>https://github.com/ryan-zheng-teki</url>
                    <summary>GitHub profile of Ryan Zheng, a software engineer with 32 repositories available.</summary>
                </item>
                <item>
                    <url>https://ryan-zheng.medium.com/from-requirements-to-automated-codebase-updates-the-role-of-precise-documentation-ab1bf0c59e3c</url>
                    <summary>Medium article by Ryan Zheng titled "From Requirements to Automated Codebase Updates: The Role of Precise Documentation — AutoByteus Part I."</summary>
                </item>
            </list>
        </arg>
        <arg name="from_role">GoogleSearchAgent</arg>
    </command>
    '''
    
    expected_tool_invocation = ToolInvocation(
        name="SendMessageTo",
        arguments={
            "to_role": "CoordinationAgent",
            "message": '''
            <list>
                <item>
                    <url>https://github.com/ryan-zheng-teki</url>
                    <summary>GitHub profile of Ryan Zheng, a software engineer with 32 repositories available.</summary>
                </item>
                <item>
                    <url>https://ryan-zheng.medium.com/from-requirements-to-automated-codebase-updates-the-role-of-precise-documentation-ab1bf0c59e3c</url>
                    <summary>Medium article by Ryan Zheng titled "From Requirements to Automated Codebase Updates: The Role of Precise Documentation — AutoByteus Part I."</summary>
                </item>
            </list>
        '''.strip(),
            "from_role": "GoogleSearchAgent"
        }
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments

def test_parse_mixed_content_xml(parser):
    response = '''
    <command name="ComplexCommand">
        <arg name="mixed_content">
            This is some text
            <nested>with a nested element</nested>
            and more text
            <another_nested attr="value">
                <deeply_nested>even deeper</deeply_nested>
            </another_nested>
            final text
        </arg>
    </command>
    '''
    
    expected_tool_invocation = ToolInvocation(
        name="ComplexCommand",
        arguments={
            "mixed_content": '''
            This is some text
            <nested>with a nested element</nested>
            and more text
            <another_nested attr="value">
                <deeply_nested>even deeper</deeply_nested>
            </another_nested>
            final text
        '''.strip()
        }
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments