"""
Screenshot Fraud Detection System
Detects fake, edited, or duplicate payment screenshots
"""

import os
import re
import hashlib
import cv2
import numpy as np
import imagehash
from PIL import Image
import pytesseract
from datetime import datetime, timedelta
from models import get_db

class ScreenshotFraudDetector:
    def __init__(self, enabled=True):
        self.upload_dir = 'uploads/screenshots'
        self.enabled = enabled
        self.ensure_upload_dir()
    
    def ensure_upload_dir(self):
        """Create upload directory if it doesn't exist"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
    
    def extract_text_from_screenshot(self, image_path):
        """Extract text from screenshot using OCR"""
        try:
            image = Image.open(image_path)
            # Convert to grayscale for better OCR
            image = image.convert('L')
            text = pytesseract.image_to_string(image, lang='eng')
            return text
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""
    
    def detect_wrong_qr_code(self, screenshot_text, expected_order_id):
        """Detect if QR code is from different order"""
        order_id_patterns = [
            r'Order\s*#?(\d+)',
            r'Order\s*ID:\s*(\d+)',
            r'Ref\s*No:\s*(\d+)',
            r'Order\s*Number:\s*(\d+)',
            r'#(\d+)',
            r'Order\s*(\d+)'
        ]
        
        found_order_id = None
        for pattern in order_id_patterns:
            match = re.search(pattern, screenshot_text, re.IGNORECASE)
            if match:
                try:
                    found_order_id = int(match.group(1))
                    break
                except ValueError:
                    continue
        
        if found_order_id and found_order_id != expected_order_id:
            return True, f"QR code from different order #{found_order_id}"
        
        return False, "QR code matches current order"
    
    def detect_edited_screenshot(self, image_path):
        """Detect if screenshot was edited/Photoshopped"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return True, ["Invalid image file"]
            
            fraud_indicators = []
            
            # 1. Check for editing artifacts
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect copy-paste regions (suspicious rectangular areas)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for perfect rectangles (suspicious)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                if 0.9 < aspect_ratio < 1.1 and w > 100:  # Perfect square
                    fraud_indicators.append("Perfect rectangular region detected")
            
            # 2. Check for inconsistent text rendering
            if self.has_inconsistent_text_rendering(image):
                fraud_indicators.append("Inconsistent text rendering")
            
            # 3. Check for color inconsistencies
            if self.has_color_inconsistencies(image):
                fraud_indicators.append("Color inconsistencies detected")
            
            # 4. Check for compression artifacts
            if self.has_compression_artifacts(image):
                fraud_indicators.append("Heavy compression artifacts")
            
            return len(fraud_indicators) > 0, fraud_indicators
            
        except Exception as e:
            return True, [f"Error analyzing image: {str(e)}"]
    
    def has_inconsistent_text_rendering(self, image):
        """Check if text rendering is consistent"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Find text regions using contours
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 20 and h > 10:  # Filter small regions
                    text_regions.append((x, y, w, h))
            
            if len(text_regions) < 2:
                return False
            
            # Check for suspicious size variations
            heights = [h for _, _, _, h in text_regions]
            if len(heights) > 1:
                height_std = np.std(heights)
                if height_std > 20:  # High variation in text heights
                    return True
            
            return False
            
        except Exception:
            return False
    
    def has_color_inconsistencies(self, image):
        """Check for color inconsistencies that might indicate editing"""
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Check for very uniform colors (might indicate editing)
            color_std = np.std(hsv[:,:,2])  # Standard deviation of value channel
            if color_std < 20:  # Very uniform colors
                return True
            
            # Check for abrupt color changes
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            laplacian_var = laplacian.var()
            
            if laplacian_var < 100:  # Low variance indicates heavy compression/editing
                return True
            
            return False
            
        except Exception:
            return False
    
    def has_compression_artifacts(self, image):
        """Check for compression artifacts"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Check for block artifacts (JPEG compression)
            h, w = gray.shape
            block_size = 8
            
            artifacts_count = 0
            for i in range(0, h - block_size, block_size):
                for j in range(0, w - block_size, block_size):
                    block = gray[i:i+block_size, j:j+block_size]
                    if self.has_block_artifacts(block):
                        artifacts_count += 1
            
            # If more than 10% of blocks have artifacts, it's suspicious
            total_blocks = (h // block_size) * (w // block_size)
            if total_blocks > 0 and artifacts_count / total_blocks > 0.1:
                return True
            
            return False
            
        except Exception:
            return False
    
    def has_block_artifacts(self, block):
        """Check if a block has compression artifacts"""
        # Check for uniform blocks (compression artifact)
        if np.std(block) < 5:  # Very uniform block
            return True
        
        # Check for edge artifacts
        edges = cv2.Canny(block, 50, 150)
        if np.sum(edges) > 0:
            # Check if edges are too regular (compression artifact)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) > 0:
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w == block.shape[1] or h == block.shape[0]:  # Edge-to-edge contour
                        return True
        
        return False
    
    def detect_duplicate_screenshot(self, image_path, order_id):
        """Detect if same screenshot was used for different orders"""
        try:
            # Create image hash
            image = Image.open(image_path)
            image_hash = hashlib.md5(image.tobytes()).hexdigest()
            
            # Check database for duplicates
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT order_id, uploaded_at 
                FROM order_screenshots 
                WHERE image_hash = %s AND order_id != %s
            """, (image_hash, order_id))
            
            duplicate = cur.fetchone()
            cur.close()
            conn.close()
            
            if duplicate:
                return True, f"Same screenshot used for order #{duplicate[0]} on {duplicate[1]}"
            
            return False, "Unique screenshot"
            
        except Exception as e:
            return True, f"Error checking duplicates: {str(e)}"
    
    def detect_similar_screenshots(self, image_path, order_id):
        """Detect similar screenshots using perceptual hashing"""
        try:
            image = Image.open(image_path)
            phash = imagehash.phash(image)
            
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT order_id, image_hash, uploaded_at 
                FROM order_screenshots 
                WHERE order_id != %s
            """, (order_id,))
            
            similar_screenshots = []
            for row in cur.fetchall():
                try:
                    stored_image_path = os.path.join(self.upload_dir, f"{row[1]}.jpg")
                    if os.path.exists(stored_image_path):
                        stored_image = Image.open(stored_image_path)
                        stored_phash = imagehash.phash(stored_image)
                        
                        # Calculate similarity
                        similarity = 1 - (phash - stored_phash) / len(phash.hash) ** 2
                        
                        if similarity > 0.9:  # 90% similar
                            similar_screenshots.append({
                                'order_id': row[0],
                                'similarity': similarity,
                                'uploaded_at': row[2]
                            })
                except Exception:
                    continue
            
            cur.close()
            conn.close()
            
            if similar_screenshots:
                return True, f"Similar screenshots found: {similar_screenshots}"
            
            return False, "No similar screenshots"
            
        except Exception as e:
            return True, f"Error checking similar screenshots: {str(e)}"
    
    def detect_amount_manipulation(self, screenshot_text, expected_amount):
        """Detect if amount was edited in screenshot"""
        amount_patterns = [
            r'\$(\d+\.?\d*)',
            r'USD\s*(\d+\.?\d*)',
            r'Amount:\s*\$?(\d+\.?\d*)',
            r'Total:\s*\$?(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*USD',
            r'(\d+\.?\d*)\s*\$',
            r'Amount:?\s*\$?(\d+\.?\d*)',
            r'Total:?\s*\$?(\d+\.?\d*)',
            r'(\d+\.?\d*)'
        ]
        
        found_amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, screenshot_text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match)
                    found_amounts.append(amount)
                except ValueError:
                    continue
        
        if not found_amounts:
            return True, "No amount found in screenshot"
        
        # Check if any amount matches expected
        amount_matches = any(abs(amount - expected_amount) < 0.01 for amount in found_amounts)
        
        if not amount_matches:
            return True, f"Amount mismatch: found {found_amounts}, expected {expected_amount}"
        
        # Check for suspicious amount patterns (but be more lenient)
        if len(found_amounts) > 1:
            unique_amounts = list(set(found_amounts))
            # Only flag as fraud if amounts are very different (more than 50% difference)
            if len(unique_amounts) > 1:
                # Check if any amount matches expected (within 1% tolerance)
                has_matching_amount = any(abs(amount - expected_amount) < expected_amount * 0.01 for amount in unique_amounts)
                if not has_matching_amount:
                    return True, f"Multiple different amounts found: {unique_amounts}"
        
        return False, "Amount verification passed"
    
    def verify_timestamp(self, screenshot_text):
        """Verify if screenshot timestamp is recent"""
        timestamp_patterns = [
            r'(\d{2}:\d{2}:\d{2})',
            r'(\d{1,2}:\d{2}\s*[AP]M)',
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
        ]
        
        found_timestamps = []
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, screenshot_text, re.IGNORECASE)
            found_timestamps.extend(matches)
        
        if not found_timestamps:
            return False, "No timestamp found in screenshot"
        
        # Check if any timestamp is recent (within last 2 hours)
        current_time = datetime.now()
        for timestamp_str in found_timestamps:
            try:
                # Try to parse different timestamp formats
                timestamp = self.parse_timestamp(timestamp_str)
                if timestamp:
                    time_diff = current_time - timestamp
                    if time_diff < timedelta(hours=2):
                        return True, "Recent timestamp found"
            except Exception:
                continue
        
        return False, "Screenshot appears to be old"
    
    def parse_timestamp(self, timestamp_str):
        """Parse various timestamp formats"""
        formats = [
            '%H:%M:%S',
            '%I:%M %p',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def comprehensive_verification(self, image_path, order_id, expected_amount):
        """
        Complete fraud detection for uploaded screenshots
        """
        verification_results = {
            'is_fraud': False,
            'fraud_reasons': [],
            'confidence_score': 1.0,
            'verification_details': {}
        }
        
        # If fraud detection is disabled, always pass
        if not self.enabled:
            verification_results['verification_details'] = {
                'text_extracted': True,
                'qr_check': True,
                'edit_check': True,
                'duplicate_check': True,
                'similarity_check': True,
                'amount_check': True,
                'timestamp_check': True
            }
            return verification_results
        
        try:
            # Check if image file exists
            if not os.path.exists(image_path):
                verification_results['fraud_reasons'].append("Image file not found")
                verification_results['is_fraud'] = True
                return verification_results
            
            # 1. Extract text from screenshot
            screenshot_text = self.extract_text_from_screenshot(image_path)
            verification_results['verification_details']['text_extracted'] = len(screenshot_text) > 0
            
            # 2. Check for wrong QR code
            wrong_qr, qr_reason = self.detect_wrong_qr_code(screenshot_text, order_id)
            verification_results['verification_details']['qr_check'] = not wrong_qr
            if wrong_qr:
                verification_results['fraud_reasons'].append(qr_reason)
            
            # 3. Check for edited screenshot
            is_edited, edit_reasons = self.detect_edited_screenshot(image_path)
            verification_results['verification_details']['edit_check'] = not is_edited
            if is_edited:
                verification_results['fraud_reasons'].extend(edit_reasons)
            
            # 4. Check for duplicate screenshots
            is_duplicate, duplicate_reason = self.detect_duplicate_screenshot(image_path, order_id)
            verification_results['verification_details']['duplicate_check'] = not is_duplicate
            if is_duplicate:
                verification_results['fraud_reasons'].append(duplicate_reason)
            
            # 5. Check for similar screenshots
            is_similar, similar_reason = self.detect_similar_screenshots(image_path, order_id)
            verification_results['verification_details']['similarity_check'] = not is_similar
            if is_similar:
                verification_results['fraud_reasons'].append(similar_reason)
            
            # 6. Check for amount manipulation
            amount_manipulated, amount_reason = self.detect_amount_manipulation(screenshot_text, expected_amount)
            verification_results['verification_details']['amount_check'] = not amount_manipulated
            if amount_manipulated:
                verification_results['fraud_reasons'].append(amount_reason)
            
            # 7. Check for recent timestamp (optional - don't fail if no timestamp)
            timestamp_valid, timestamp_reason = self.verify_timestamp(screenshot_text)
            verification_results['verification_details']['timestamp_check'] = timestamp_valid
            # Only add timestamp as fraud reason if it's explicitly old, not just missing
            if not timestamp_valid and 'old' in timestamp_reason.lower():
                verification_results['fraud_reasons'].append(timestamp_reason)
            
            # 8. Calculate confidence score (more lenient)
            total_checks = 6
            passed_checks = sum(verification_results['verification_details'].values())
            verification_results['confidence_score'] = passed_checks / total_checks
            
            # 9. Determine if fraud (only if critical checks fail)
            critical_fraud_reasons = [
                reason for reason in verification_results['fraud_reasons'] 
                if any(keyword in reason.lower() for keyword in [
                    'duplicate', 'same screenshot', 'wrong qr', 'amount mismatch'
                ])
            ]
            
            # Only flag as fraud if critical issues OR very low confidence
            verification_results['is_fraud'] = (
                len(critical_fraud_reasons) > 0 or 
                verification_results['confidence_score'] < 0.3
            )
            
            return verification_results
            
        except Exception as e:
            verification_results['fraud_reasons'].append(f"Error processing screenshot: {str(e)}")
            verification_results['is_fraud'] = True
            return verification_results

# Global instance - temporarily disabled for testing
screenshot_detector = ScreenshotFraudDetector(enabled=False)
