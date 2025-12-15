#!/usr/bin/env python3
"""
Conversational AI Agent for RDBMS Builder

An intelligent agent that:
- Classifies user intent (software development related or not)
- Asks for more details when needed
- Generates database schemas and NestJS architecture
- Answers questions about generated outputs
- Uses long-term memory for context-aware conversations
"""

from .graph.nodes.intent_classifier import intent_classifier, IntentClassification
from .graph.nodes.qa_agent import qa_agent
from main import run_builder, save_outputs
from .utils.checkpoint_manager import CheckpointManager, CheckpointerType
from .utils.state_manager import StateManager
from .utils.thread_manager import get_or_create_thread_id
from typing import Optional
import sys


class ConversationalAgent:
    """Intelligent conversational agent for RDBMS building."""
    
    def __init__(
        self,
        checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
        checkpoint_connection: Optional[str] = None
    ):
        self.checkpoint_type = checkpoint_type
        self.checkpoint_connection = checkpoint_connection or "./data/checkpoints.db"
        self.thread_id = get_or_create_thread_id()
        self.state = None
        self.conversation_history = []
        
    def start(self):
        """Start the conversational interface."""
        print("\n" + "=" * 70)
        print("🤖 AI SOFTWARE ARCHITECT ASSISTANT")
        print("=" * 70)
        print("\nI can help you design database schemas and NestJS backend architectures.")
        print("Ask me anything about software development, and I'll guide you!")
        print("\nCommands:")
        print("  - 'save' - Save generated outputs")
        print("  - 'show' - Show current state summary")
        print("  - 'reset' - Start a new conversation")
        print("  - 'exit' - Exit the chat")
        print("=" * 70)
        
        # Initialize state
        self.state = StateManager.create_initial_state(
            requirements="",
            dialect="postgresql",
            enable_critic=False,
            generate_nestjs=True,
            thread_id=self.thread_id
        )
        
        # Try to load from checkpoint
        self._load_checkpoint()
        
        # Start conversation loop
        self.conversation_loop()
    
    def _load_checkpoint(self):
        """Try to load existing checkpoint for this thread."""
        try:
            checkpoint_manager = CheckpointManager(
                checkpointer_type=self.checkpoint_type,
                connection_string=self.checkpoint_connection
            )
            
            existing_state = checkpoint_manager.get_state(self.thread_id)
            if existing_state:
                print(f"\n📂 Loaded previous session (Thread: {self.thread_id[:8]}...)")
                self.state = existing_state
                
                # Show previous context
                working = self.state.get("working", {})
                if working.get("tables"):
                    print(f"   • Previous work: {len(working['tables'])} tables designed")
        except Exception as e:
            # No checkpoint or error loading - that's okay, start fresh
            pass
    
    def conversation_loop(self):
        """Main conversation loop."""
        while True:
            try:
                # Get user input
                print("\n" + "─" * 70)
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == 'exit':
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'save':
                    self._save_outputs()
                    continue
                elif user_input.lower() == 'show':
                    self._show_state()
                    continue
                elif user_input.lower() == 'reset':
                    self._reset_conversation()
                    continue
                
                # Process user input
                self._process_input(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    def _process_input(self, user_input: str):
        """Process user input through the agent."""
        # Update state with user input
        self.state["working"]["user_requirements"] = user_input
        self.conversation_history.append({"role": "user", "content": user_input})
        
        print("\n🤖 Assistant: ", end="", flush=True)
        
        # Step 1: Classify intent
        classification_result = intent_classifier(self.state)
        self.state["working"].update(classification_result.get("working", {}))
        
        classification = self.state["working"].get("intent_classification", {})
        
        # Check if relevant
        if not classification.get("is_relevant"):
            response = (
                "I apologize, but that doesn't seem to be related to software development, "
                "database design, or system architecture.\n\n"
                "I specialize in:\n"
                "  • Database schema design\n"
                "  • NestJS backend architecture\n"
                "  • API design and structure\n"
                "  • System architecture planning\n\n"
                "How can I help you with your software project?"
            )
            print(response)
            self.conversation_history.append({"role": "assistant", "content": response})
            return
        
        intent_type = classification.get("intent_type")
        
        # Step 2: Route based on intent
        if intent_type in ["new_project", "modification"]:
            self._handle_generation(user_input, classification)
        elif intent_type in ["question", "explanation"]:
            self._handle_question(user_input)
        else:
            # Ask for clarification
            response = (
                f"{classification.get('reasoning')}\n\n"
                f"{classification.get('suggested_action')}\n\n"
                "Could you provide more details about what you'd like to build?"
            )
            print(response)
            self.conversation_history.append({"role": "assistant", "content": response})
    
    def _handle_generation(self, user_input: str, classification: dict):
        """Handle schema generation or modification."""
        print(f"I'll help you {classification.get('reasoning', 'design your system').lower()}.\n")
        
        # Check if we need more details
        if len(user_input.split()) < 15:  # Simple heuristic
            print("To create a comprehensive design, I need a bit more information.\n")
            print("Please describe:")
            print("  • What kind of system are you building?")
            print("  • What are the main features or entities?")
            print("  • Who will use it and how?")
            print("\nOr just say 'continue' if you've provided enough details.")
            return
        
        print("Generating your database schema and NestJS architecture...\n")
        
        # Run the builder
        try:
            result = run_builder(
                requirements=user_input,
                dialect="postgresql",
                enable_critic=False,  # Faster for conversational mode
                generate_nestjs=True,
                interactive=False,
                thread_id=self.thread_id,
                enable_checkpointing=True,
                checkpoint_type=self.checkpoint_type,
                checkpoint_connection=self.checkpoint_connection
            )
            
            # Update state
            self.state = result
            
            # Show summary
            working = result.get("working", {})
            archive = result.get("archive", {})
            
            response = "✅ Generation complete!\n\n"
            response += f"📊 Created {len(working.get('entities', []))} entities and {len(working.get('tables', []))} database tables\n"
            
            if archive.get("nestjs_architecture"):
                arch = archive["nestjs_architecture"]
                response += f"🚀 Generated {len(arch.get('modules', []))} NestJS modules with {len(arch.get('endpoints', []))} API endpoints\n"
            
            response += "\n💡 You can now ask me questions like:\n"
            response += "  • 'Explain the user authentication endpoints'\n"
            response += "  • 'How does the database handle relationships?'\n"
            response += "  • 'Show me the API structure'\n"
            response += "  • 'Add a new feature for...'\n"
            response += "\nOr type 'save' to save the outputs to files."
            
            print(response)
            self.conversation_history.append({"role": "assistant", "content": response})
            
        except Exception as e:
            error_msg = f"I encountered an error while generating: {str(e)}\nPlease try rephrasing your requirements."
            print(error_msg)
            self.conversation_history.append({"role": "assistant", "content": error_msg})
    
    def _handle_question(self, user_question: str):
        """Handle questions about previously generated outputs."""
        # Check if we have previous output
        archive = self.state.get("archive", {})
        if not (archive.get("ddl_script") or archive.get("nestjs_architecture")):
            response = (
                "I haven't generated any schema or architecture yet. "
                "Please first describe the system you'd like me to design, then I can answer questions about it!"
            )
            print(response)
            self.conversation_history.append({"role": "assistant", "content": response})
            return
        
        # Use Q&A agent
        qa_result = qa_agent(self.state)
        self.state["working"].update(qa_result.get("working", {}))
        self.state["archive"].update(qa_result.get("archive", {}))
        
        answer = self.state["working"].get("last_answer", "I couldn't generate an answer.")
        print(answer)
        self.conversation_history.append({"role": "assistant", "content": answer})
    
    def _save_outputs(self):
        """Save generated outputs to files."""
        if not self.state:
            print("No outputs to save yet.")
            return
        
        try:
            save_outputs(self.state)
            print("\n✅ Outputs saved successfully!")
        except Exception as e:
            print(f"\n❌ Error saving outputs: {e}")
    
    def _show_state(self):
        """Show current state summary."""
        if not self.state:
            print("No state information available.")
            return
        
        working = self.state.get("working", {})
        archive = self.state.get("archive", {})
        
        print("\n" + "=" * 70)
        print("📊 CURRENT STATE")
        print("=" * 70)
        print(f"\nThread ID: {self.thread_id[:16]}...")
        print(f"Entities: {len(working.get('entities', []))}")
        print(f"Tables: {len(working.get('tables', []))}")
        print(f"LLM Calls: {archive.get('total_llm_calls', 0)}")
        print(f"Has DDL: {'Yes' if archive.get('ddl_script') else 'No'}")
        print(f"Has NestJS: {'Yes' if archive.get('nestjs_architecture') else 'No'}")
        print(f"Q&A History: {len(archive.get('qa_history', []))} exchanges")
        print("=" * 70)
    
    def _reset_conversation(self):
        """Reset to a new conversation."""
        confirm = input("Start a new conversation? This will create a new thread. [y/N]: ").strip().lower()
        if confirm == 'y':
            self.thread_id = get_or_create_thread_id()
            self.state = StateManager.create_initial_state(
                requirements="",
                dialect="postgresql",
                enable_critic=False,
                generate_nestjs=True,
                thread_id=self.thread_id
            )
            self.conversation_history = []
            print(f"\n✅ New conversation started (Thread: {self.thread_id[:8]}...)")


def main():
    """Main entry point for conversational mode."""
    print("\n🚀 Starting Conversational AI Agent...")
    
    agent = ConversationalAgent(
        checkpoint_type=CheckpointerType.SQLITE,
        checkpoint_connection="./data/checkpoints.db"
    )
    
    agent.start()


if __name__ == "__main__":
    main()

