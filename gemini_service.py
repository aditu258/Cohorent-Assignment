import google.generativeai as genai
import os

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCYvmNfbSxbhh_mBDpxWPGIVdUsx-GruWo"  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

# Configure generation config for better compatibility
generation_config = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 2048,
}

def generate_summary_with_gemini(patient_stories):
    """Generate a 2-line summary using Gemini API"""
    try:
        if not patient_stories:
            return "No patient stories available for summary."
        
        # Prepare the prompt for Gemini
        stories_text = "\n\n".join([f"Story {i+1}: {story}" for i, story in enumerate(patient_stories[:10])])
        
        prompt = f"""
        Based on the following patient stories and reviews about a doctor, provide a concise 2-line paragraph summary highlighting the key pros and cons, and overall recommendation.

        Patient Stories:
        {stories_text}

        Please provide exactly 2 lines as a natural paragraph (no "Line 1:" or "Line 2:" labels):
        First line: Key strengths and positive aspects
        Second line: Areas of concern (if any) and overall recommendation

        Write as a natural flowing paragraph with just 2 lines.
        """
        
        # Try different model names - prioritize Gemini Flash
        model_names = ['gemini-2.5-flash']
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name, generation_config=generation_config)
                response = model.generate_content(prompt)
                
                summary = response.text.strip()
                
                return summary
                
            except Exception as model_error:
                continue
        
        # If all models fail, create a simple summary manually
        return create_manual_summary(patient_stories)
        
    except Exception as e:
        return "Summary generation failed."

def create_manual_summary(patient_stories):
    """Create a simple manual summary when Gemini API fails"""
    try:
        if not patient_stories:
            return "No patient stories available for summary."
        
        # Count positive and negative keywords
        positive_keywords = ['good', 'excellent', 'great', 'amazing', 'satisfied', 'recommend', 'best', 'professional', 'caring', 'gentle', 'painless', 'comfortable']
        negative_keywords = ['bad', 'poor', 'terrible', 'painful', 'expensive', 'rude', 'unprofessional', 'disappointed', 'worst', 'avoid']
        
        positive_count = 0
        negative_count = 0
        
        for story in patient_stories:
            story_lower = story.lower()
            for keyword in positive_keywords:
                if keyword in story_lower:
                    positive_count += 1
            for keyword in negative_keywords:
                if keyword in story_lower:
                    negative_count += 1
        
        # Create summary based on sentiment
        if positive_count > negative_count:
            line1 = f"Positive feedback with {positive_count} positive mentions including professional care and patient satisfaction."
            line2 = f"Overall recommended based on {len(patient_stories)} patient reviews."
        elif negative_count > positive_count:
            line1 = f"Mixed feedback with {negative_count} concerns mentioned by patients."
            line2 = f"Consider with caution based on {len(patient_stories)} patient reviews."
        else:
            line1 = f"Balanced feedback with {positive_count} positive and {negative_count} negative mentions."
            line2 = f"Mixed recommendations from {len(patient_stories)} patient reviews."
        
        manual_summary = f"{line1}\n{line2}"
        
        return manual_summary
        
    except Exception as e:
        return f"Summary based on {len(patient_stories)} patient reviews."
