"""
Gemini AI client for handling text generation and conversations
"""
import google.generativeai as genai
from typing import Optional, List, Dict
import asyncio
from functools import partial

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google API key for Gemini
            model_name: Model to use (gemini-1.5-flash, gemini-1.5-pro, etc.)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.chat_sessions = {}  # Store chat sessions per user
        
    async def generate_response(
        self,
        prompt: str,
        user_id: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        use_chat_history: bool = True,
        language: str = "ar"
    ) -> str:
        """
        Generate response using Gemini
        
        Args:
            prompt: User input text
            user_id: Telegram user ID for maintaining chat history
            temperature: Creativity of responses (0.0 to 1.0)
            max_tokens: Maximum length of response
            use_chat_history: Whether to use conversation history
            
        Returns:
            Generated text response
        """
        try:
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Add safety settings to reduce blocking
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            # Add language instruction to prompt
            if language == "ar":
                enhanced_prompt = f"أجب باللغة العربية فقط. {prompt}"
            else:
                enhanced_prompt = prompt

            # DEBUG: Print what we're sending to Gemini
            print("\n" + "="*80)
            print("📤 SENDING TO GEMINI (GENERATE_RESPONSE):")
            print("="*80)
            print(f"User ID: {user_id}")
            print(f"Language: {language}")
            print(f"Use chat history: {use_chat_history}")
            print(f"Prompt length: {len(enhanced_prompt)} characters")
            print(f"\nFirst 300 chars of prompt:\n{enhanced_prompt[:300]}")
            if len(enhanced_prompt) > 300:
                print(f"\n... [truncated {len(enhanced_prompt) - 300} characters] ...")
            print("="*80 + "\n")

            # Use chat session for conversation history
            if use_chat_history and user_id:
                if user_id not in self.chat_sessions:
                    self.chat_sessions[user_id] = self.model.start_chat(history=[])

                chat = self.chat_sessions[user_id]
                # Run async in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    partial(chat.send_message, enhanced_prompt, generation_config=generation_config, safety_settings=safety_settings)
                )
            else:
                # Single prompt without history
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    partial(self.model.generate_content, enhanced_prompt, generation_config=generation_config, safety_settings=safety_settings)
                )

            # DEBUG: Print what we received from Gemini
            print("\n" + "="*80)
            print("📥 RECEIVED FROM GEMINI (GENERATE_RESPONSE):")
            print("="*80)
            print(f"Has candidates: {hasattr(response, 'candidates')}")
            if hasattr(response, 'candidates'):
                print(f"Number of candidates: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    candidate = response.candidates[0]
                    print(f"Finish reason: {candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'N/A'}")
                    if hasattr(candidate, 'safety_ratings'):
                        print(f"Safety ratings:")
                        for rating in candidate.safety_ratings:
                            print(f"  - {rating.category}: {rating.probability}")
            print("="*80 + "\n")

            # Check candidates BEFORE accessing .text
            if not hasattr(response, 'candidates') or not response.candidates:
                return "عذراً، لم يتم الحصول على رد."

            candidate = response.candidates[0]

            # Check finish_reason
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason

                if finish_reason == 2:  # SAFETY
                    return "عذراً، تم حظر هذا المحتوى بواسطة إعدادات الأمان. حاول مع سؤال مختلف."
                elif finish_reason == 3:  # RECITATION
                    return "عذراً، هذا المحتوى محمي بحقوق الطبع والنشر."
                elif finish_reason == 4:  # OTHER
                    return "عذراً، فشل في إنشاء الرد."

            # Safely get text
            try:
                result_text = response.text
                print(f"✅ Successfully generated response ({len(result_text)} chars)")
                print(f"First 200 chars: {result_text[:200]}")
                if len(result_text) > 200:
                    print(f"... [truncated {len(result_text) - 200} characters]")
                return result_text
            except Exception as text_error:
                print(f"⚠️ Failed to get response.text: {text_error}")
                try:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        if candidate.content.parts:
                            result_text = candidate.content.parts[0].text
                            print(f"✅ Extracted from parts ({len(result_text)} chars)")
                            return result_text
                except Exception as parts_error:
                    print(f"⚠️ Failed to extract from parts: {parts_error}")
                    pass

                return "عذراً، لم أتمكن من إنشاء رد مناسب."

        except Exception as e:
            print(f"Error generating response: {e}")
            return f"عذراً، حدث خطأ في توليد الرد: {str(e)}"
    
    async def summarize_text(self, text: str, language: str = "ar") -> str:
        """
        Summarize given text

        Args:
            text: Text to summarize
            language: Language for summary (ar for Arabic, en for English)

        Returns:
            Summary of the text
        """
        try:
            if language == "ar":
                prompt = f"قم بتلخيص النص التالي باللغة العربية بشكل مختصر ومفيد:\n\n{text}"
            else:
                prompt = f"Please summarize the following text concisely:\n\n{text}"

            # DEBUG: Print what we're sending to Gemini
            print("\n" + "="*80)
            print("📤 SENDING TO GEMINI (SUMMARIZE):")
            print("="*80)
            print(f"Prompt length: {len(prompt)} characters")
            print(f"Text to summarize length: {len(text)} characters")
            print(f"\nFirst 500 chars of prompt:\n{prompt[:500]}")
            if len(prompt) > 500:
                print(f"\n... [truncated {len(prompt) - 500} characters] ...")
            print("="*80 + "\n")

            generation_config = genai.GenerationConfig(
                temperature=0.3,  # Lower temperature for more focused summaries
                max_output_tokens=2048,  # Increased from 200 to allow longer summaries
            )

            # Add safety settings to reduce blocking
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    self.model.generate_content,
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            )

            # DEBUG: Print what we received from Gemini
            print("\n" + "="*80)
            print("📥 RECEIVED FROM GEMINI (SUMMARIZE):")
            print("="*80)
            print(f"Has candidates: {hasattr(response, 'candidates')}")
            if hasattr(response, 'candidates'):
                print(f"Number of candidates: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'N/A'
                    print(f"Finish reason: {finish_reason}")

                    # Print safety ratings in detail
                    if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                        print(f"\nSafety ratings (blocking if MEDIUM/HIGH):")
                        for rating in candidate.safety_ratings:
                            try:
                                category = rating.category.name if hasattr(rating.category, 'name') else str(rating.category)
                                probability = rating.probability.name if hasattr(rating.probability, 'name') else str(rating.probability)
                                print(f"  - {category}: {probability}")
                            except Exception as e:
                                print(f"  - [Error printing rating: {e}]")
                    else:
                        print("No safety ratings available")

                    # If blocked, try to get block reason
                    if finish_reason == 2:
                        print("\n⚠️  CONTENT BLOCKED BY SAFETY FILTERS!")
                        print("This is likely a false positive. The report content is being flagged incorrectly.")
            print("="*80 + "\n")

            # IMPORTANT: Check candidates BEFORE trying to access .text
            # because .text throws exception if content was blocked
            if not hasattr(response, 'candidates') or not response.candidates:
                return "لا يوجد رد من النموذج" if language == "ar" else "No response from model"

            candidate = response.candidates[0]

            # Check finish_reason to see why generation stopped
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason

                # finish_reason values: 0=UNSPECIFIED, 1=STOP (success), 2=SAFETY, 3=RECITATION, 4=OTHER
                if finish_reason == 2:  # SAFETY
                    # Content blocked by safety filters
                    safety_msg = "تم حظر المحتوى بواسطة فلاتر الأمان.\n\n"
                    safety_msg += "السبب المحتمل: المحادثات تحتوي على محتوى حساس.\n"
                    safety_msg += "الحل: حاول مع محادثات مختلفة أو استخدم /clear لمسح المحادثات."
                    return safety_msg if language == "ar" else "Content blocked by safety filters. Try different conversations."

                elif finish_reason == 3:  # RECITATION
                    return "المحتوى محمي بحقوق النشر" if language == "ar" else "Content protected by copyright"

                elif finish_reason == 4:  # OTHER
                    return "فشل في التلخيص لأسباب فنية" if language == "ar" else "Failed due to technical reasons"

            # If finish_reason is 1 (STOP - success), safely get the text
            try:
                result_text = response.text
                print(f"✅ Successfully extracted response text ({len(result_text)} chars)")
                print(f"First 200 chars: {result_text[:200]}")
                if len(result_text) > 200:
                    print(f"... [truncated {len(result_text) - 200} characters]")
                return result_text
            except Exception as text_error:
                print(f"⚠️ Failed to get response.text: {text_error}")
                # Fallback: try to extract from parts directly
                try:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        if candidate.content.parts:
                            result_text = candidate.content.parts[0].text
                            print(f"✅ Extracted from parts ({len(result_text)} chars)")
                            return result_text
                except Exception as parts_error:
                    print(f"⚠️ Failed to extract from parts: {parts_error}")
                    pass

                return "لا يمكن استخراج النص من الرد" if language == "ar" else "Cannot extract text from response"

        except Exception as e:
            error_msg = str(e)
            print(f"Error summarizing text: {error_msg}")

            # Return detailed error for debugging
            if language == "ar":
                return f"عذراً، حدث خطأ في التلخيص:\n{error_msg}"
            else:
                return f"Sorry, error in summarization:\n{error_msg}"
    
    def clear_chat_history(self, user_id: int):
        """
        Clear chat history for a specific user
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]
    
    async def analyze_image(self, image_path: str, prompt: str = "What's in this image?") -> str:
        """
        Analyze an image using Gemini's vision capabilities
        
        Args:
            image_path: Path to the image file
            prompt: Question about the image
            
        Returns:
            Analysis of the image
        """
        try:
            # For vision tasks, use gemini-1.5-flash or gemini-1.5-pro
            vision_model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Upload the image
            image = genai.upload_file(image_path)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(vision_model.generate_content, [prompt, image])
            )
            
            return response.text
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return f"عذراً، حدث خطأ في تحليل الصورة: {str(e)}"