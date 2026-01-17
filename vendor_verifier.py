import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import base64

# Page config
st.set_page_config(
    page_title="Zolarux Vendor Verification Tool",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-card-initial {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .score-display {
        font-size: 3rem;
        font-weight: bold;
    }
    .section-header {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .quality-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'vendor_data' not in st.session_state:
    st.session_state.vendor_data = {}
if 'final_result' not in st.session_state:
    st.session_state.final_result = None

# --- SIDEBAR: MODE SELECTION ---
with st.sidebar:
    st.image("https://zolarux.com.ng/images/logo.png", width=150)
    st.title("Admin Controls")
    
    # The Mode Switch
    verification_mode_selection = st.radio(
        "Verification Mode",
        options=["INITIAL (WhatsApp)", "FULL (Platform)"],
        index=0,
        help="INITIAL: Fast check for WhatsApp access. FULL: Detailed scoring for loans & platform benefits."
    )
    
    # Store mode in simple variable for logic checks
    MODE = "INITIAL" if "INITIAL" in verification_mode_selection else "FULL"
    st.session_state.verification_mode = MODE
    
    st.info(f"Currently running: **{MODE} VERIFICATION**")
    if MODE == "INITIAL":
        st.caption("✅ Fast Track\n✅ Pass/Fail Only\n✅ 30-Day Validity")
    else:
        st.caption("🛡️ Deep Dive\n🛡️ 100-Point Score\n🛡️ Long-term Trust")

# Scoring & Logic Class
class VendorScorerV3:
    def __init__(self, data, mode="FULL"):
        self.data = data
        self.mode = mode
        self.score = 0
        self.category_scores = {}
        self.recommendations = []
        self.risk_factors = []
    
    # --- LOGIC FOR INITIAL MODE ---
    def assess_initial_verification(self):
        """Binary Pass/Fail logic for WhatsApp verification"""
        checks = []
        
        # 1. Critical Data Presence
        if not self.data.get('has_name'): checks.append("Missing Business Name")
        if not self.data.get('has_phone'): checks.append("Missing Phone Number")
        if not self.data.get('has_location'): checks.append("Missing Location")
        if not self.data.get('has_id_photo'): checks.append("Missing ID Verification")
        if not self.data.get('has_supplier_proof') and not self.data.get('has_operations_proof'): 
            checks.append("No Proof of Stock/Operations")
        
        # 2. Process Compliance
        if not self.data.get('agreed_to_rules'): checks.append("Did not agree to Escrow Rules")
        if not self.data.get('video_call_verified'): checks.append("Video Call Not Completed")
        
        # 3. Behavioral Flags
        if self.data.get('red_flags_count', 0) > 0: checks.append(f"Found {self.data.get('red_flags_count')} Red Flags")
        if self.data.get('responsiveness_rating', 3) < 2: checks.append("Responsiveness too low")

        # Result
        passed = len(checks) == 0
        
        return {
            'passed': passed,
            'issues': checks,
            'badge': '🔵 WhatsApp Verified' if passed else '🔴 Verification Failed',
            'status': 'PROVISIONALLY VERIFIED' if passed else 'FAILED',
            'description': 'Valid for 30 Days. Subject to Full Verification.',
            'color': '#2563eb' if passed else '#ef4444'
        }

    # --- LOGIC FOR FULL MODE (Existing 100-Point System) ---
    def calculate_auto_score(self):
        score = 0
        # Basic Info (15 pts)
        if self.data.get('has_name'): score += 3
        if self.data.get('has_phone'): score += 4
        if self.data.get('has_address'): score += 4
        if self.data.get('has_social_media'): score += 4
        self.category_scores['Basic Information'] = score
        
        # Documents (25 pts)
        doc_score = 0
        if self.data.get('has_id_photo'): doc_score += 5
        doc_score += self.data.get('guarantor_count', 0) * 2.5
        reg_points = {'none': 0, 'smedan': 3, 'cac': 5}
        doc_score += reg_points.get(self.data.get('registration_type', 'none'), 0)
        if self.data.get('has_supplier_proof'): doc_score += 5
        if self.data.get('has_operations_proof'): doc_score += 5
        if self.data.get('has_testimonials'): doc_score += 2.5
        self.category_scores['Documents Submitted'] = doc_score
        score += doc_score
        return score
    
    def calculate_quality_score(self):
        quality_points = {'poor': 1, 'acceptable': 3, 'excellent': 5}
        score = 0
        score += quality_points.get(self.data.get('id_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('registration_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('supplier_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('operations_quality', 'poor'), 0)
        
        testimonial_points = {'suspicious': 0, 'mixed': 5, 'authentic': 10}
        score += testimonial_points.get(self.data.get('testimonial_quality', 'suspicious'), 0)
        
        if self.data.get('has_refund_policy'): score += 2.5
        if self.data.get('has_delivery_info'): score += 2.5
        
        self.category_scores['Document Quality'] = score
        return score
    
    def calculate_interaction_score(self):
        score = 0
        score += self.data.get('responsiveness_rating', 1) * 2
        comm_points = {'unprofessional': 0, 'professional': 10}
        score += comm_points.get(self.data.get('communication_quality', 'unprofessional'), 0)
        
        red_flags = self.data.get('red_flags_count', 0)
        penalty = min(red_flags * 5, score)
        score -= penalty
        
        self.category_scores['WhatsApp Interaction'] = score
        if red_flags > 0: self.category_scores['Red Flags Penalty'] = -penalty
        return score

    def calculate_total_score(self):
        if self.mode == "INITIAL":
            return None # Initial mode doesn't use scores
            
        auto_score = self.calculate_auto_score()
        quality_score = self.calculate_quality_score()
        interaction_score = self.calculate_interaction_score()
        self.score = auto_score + quality_score + interaction_score
        return self.score

    def get_full_badge(self):
        if self.score >= 80:
            return {'badge': '🟢 Green (Verified)', 'status': 'APPROVED', 'description': 'Low risk. Eligible for Loans.', 'color': '#10b981'}
        elif self.score >= 60:
            return {'badge': '🟡 Yellow (Conditional)', 'status': 'CONDITIONAL', 'description': 'Medium risk. Monitor closely.', 'color': '#f59e0b'}
        else:
            return {'badge': '🔴 Red (Rejected)', 'status': 'REJECTED', 'description': 'High risk. Do not onboard.', 'color': '#ef4444'}

# Header
st.title("🛡️ Zolarux Verification")
if MODE == "INITIAL":
    st.markdown("### 🔵 Mode: Initial WhatsApp Verification (Fast-Track)")
else:
    st.markdown("### 🟢 Mode: Full Platform Verification (Deep-Dive)")

# Progress indicator
col1, col2, col3 = st.columns(3)
with col1:
    status1 = "✅" if st.session_state.current_step > 1 else "📝" if st.session_state.current_step == 1 else "⏸️"
    st.markdown(f"### {status1} Data Collection")
with col2:
    status2 = "✅" if st.session_state.current_step > 2 else "📝" if st.session_state.current_step == 2 else "⏸️"
    st.markdown(f"### {status2} Validation")
with col3:
    status3 = "✅" if st.session_state.current_step > 3 else "📝" if st.session_state.current_step == 3 else "⏸️"
    st.markdown(f"### {status3} Decision")

st.markdown("---")

# ==========================================
# STEP 1: DATA ENTRY
# ==========================================
if st.session_state.current_step == 1:
    st.markdown(f'<div class="section-header"><h2>📋 Step 1: {MODE} Data Collection</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📝 Vendor Identity")
        vendor_name = st.text_input("Business/Vendor Name *", key="vendor_name")
        vendor_phone = st.text_input("Phone Number *", key="vendor_phone")
        
        # New: Location is critical for Initial
        vendor_location = st.text_input("Location (City/State) *", key="vendor_location")
        
        vendor_category = st.selectbox("Category", 
            ["", "Electronics", "Fashion", "Beauty", "Services", "Dropshipping", "Gadgets", "Other"],
            key="vendor_category"
        )
        
        # Only ask for Email in FULL mode, optional in INITIAL
        if MODE == "FULL":
            vendor_email = st.text_input("Email Address", key="vendor_email")
        else:
            vendor_email = "N/A (Initial)"
            
        assessment_date = st.date_input("Assessment Date", datetime.now(), key="assessment_date")
        
        st.markdown("#### ✅ Verification Checks")
        has_name = st.checkbox("Name Provided", value=True, key="has_name")
        has_phone = st.checkbox("Phone Validated", value=True, key="has_phone")
        has_location = st.checkbox("Location Provided", value=True, key="has_location")
        
        # Address is full address in Full mode
        if MODE == "FULL":
            has_address = st.checkbox("Full Address Verified", key="has_address")
            has_social_media = st.checkbox("Social Media Links", key="has_social_media")
        else:
            has_address = True # Assumed covered by location in initial
            has_social_media = st.checkbox("Social Media (Optional)", key="has_social_media")

    with col2:
        st.markdown("#### 📎 Proofs Submitted")
        has_id_photo = st.checkbox("Valid ID (NIN/Voter/Passport) *", key="has_id_photo")
        
        # Simplified proof for Initial
        st.markdown("**Proof of Stock / Operations**")
        has_supplier_proof = st.checkbox("Supplier/Stock Proof (Video/Pic)", key="has_supplier_proof")
        has_operations_proof = st.checkbox("Past Operations (Waybills/Chats)", key="has_operations_proof")
        
        has_testimonials = st.checkbox("Customer Testimonials", key="has_testimonials")
        
        # INITIAL SPECIFIC CHECKS
        st.markdown("#### 🤝 Agreements")
        agreed_to_rules = st.checkbox("Agreed to Escrow Rules *", key="agreed_to_rules")
        video_call_verified = st.checkbox("Video Call Verification Passed *", key="video_call_verified")

        # FULL MODE EXTRAS (Hidden in Initial)
        if MODE == "FULL":
            st.markdown("---")
            st.markdown("#### 🟢 Full Verification Extras")
            guarantor_count = st.radio("Guarantors", [0, 1, 2], key="guarantor_count")
            registration_type = st.selectbox("Registration", ["none", "smedan", "cac"], key="registration_type")
            has_refund_policy = st.checkbox("Refund Policy", key="has_refund_policy")
            has_delivery_info = st.checkbox("Delivery Info", key="has_delivery_info")
        else:
            # Default values for Initial mode to prevent errors
            guarantor_count = 0
            registration_type = "none"
            has_refund_policy = False
            has_delivery_info = False

    if st.button("Continue →", type="primary", use_container_width=True):
        if not vendor_name or not vendor_phone:
            st.error("⚠️ Business Name and Phone are required.")
        else:
            # Save to session
            st.session_state.vendor_data.update({
                'vendor_name': vendor_name, 'vendor_phone': vendor_phone, 
                'vendor_location': vendor_location, 'vendor_email': vendor_email,
                'vendor_category': vendor_category, 'assessment_date': assessment_date,
                'has_name': has_name, 'has_phone': has_phone, 'has_location': has_location,
                'has_address': has_address, 'has_social_media': has_social_media,
                'has_id_photo': has_id_photo, 'has_supplier_proof': has_supplier_proof,
                'has_operations_proof': has_operations_proof, 'has_testimonials': has_testimonials,
                'agreed_to_rules': agreed_to_rules, 'video_call_verified': video_call_verified,
                'guarantor_count': guarantor_count, 'registration_type': registration_type,
                'has_refund_policy': has_refund_policy, 'has_delivery_info': has_delivery_info
            })
            st.session_state.current_step = 2
            st.rerun()

# ==========================================
# STEP 2: DOCUMENT REVIEW
# ==========================================
elif st.session_state.current_step == 2:
    st.markdown('<div class="section-header"><h2>🔍 Step 2: Quality Review</h2></div>', unsafe_allow_html=True)
    
    if MODE == "INITIAL":
        st.info("ℹ️ **INITIAL MODE:** Simplified review. Ensure documents look legitimate. No granular scoring.")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**ID Card Status:**")
            id_quality = st.radio("ID Legibility", ["Clear", "Blurry/Fake"], key="id_quality_init")
        with col2:
            st.write("**Stock Proof Status:**")
            stock_quality = st.radio("Stock/Ops Proof", ["Convincing", "Suspicious"], key="stock_quality_init")
            
        # Map simple inputs to complex keys for backend compatibility
        id_q = 'excellent' if id_quality == 'Clear' else 'poor'
        sup_q = 'excellent' if stock_quality == 'Convincing' else 'poor'
        
        # Defaults for ignored fields
        registration_quality = 'poor'
        operations_quality = sup_q
        supplier_quality = sup_q
        testimonial_quality = 'mixed'

    else:
        # FULL MODE SLIDERS
        st.info("📌 **FULL MODE:** Detailed quality scoring for credit worthiness.")
        col1, col2 = st.columns(2)
        with col1:
            id_q = st.select_slider("ID Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="id_q")
            registration_quality = st.select_slider("Reg Doc Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="reg_q")
            supplier_quality = st.select_slider("Supplier Proof Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="sup_q")
        with col2:
            operations_quality = st.select_slider("Ops Proof Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="ops_q")
            testimonial_quality = st.select_slider("Testimonial Auth", ['suspicious', 'mixed', 'authentic'], value='mixed', key="test_q")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back"):
            st.session_state.current_step = 1
            st.rerun()
    with col_next:
        if st.button("Continue →", type="primary"):
            st.session_state.vendor_data.update({
                'id_quality': id_q,
                'registration_quality': registration_quality,
                'supplier_quality': supplier_quality,
                'operations_quality': operations_quality if MODE == "FULL" else sup_q,
                'testimonial_quality': testimonial_quality if MODE == "FULL" else 'mixed'
            })
            st.session_state.current_step = 3
            st.rerun()

# ==========================================
# STEP 3: INTERACTION ASSESSMENT
# ==========================================
elif st.session_state.current_step == 3:
    st.markdown('<div class="section-header"><h2>💬 Step 3: Interaction & Risk</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ⚡ Responsiveness")
        responsiveness_rating = st.slider("Response Speed (1=Slow, 5=Fast)", 1, 5, 3, key="resp_rate")
        
        st.markdown("#### 💬 Communication")
        communication_quality = st.radio("Style", ['unprofessional', 'professional'], index=1, format_func=lambda x: x.title(), key="comm_q")
    
    with col2:
        st.markdown("#### 🚩 Red Flags (Crucial)")
        red_flags_count = st.number_input("Count of Red Flags", 0, 10, 0, help="Evasive answers, pressure tactics, mismatched names", key="red_flags")
        
        if red_flags_count > 0:
            red_flags_notes = st.text_area("Describe Red Flags", placeholder="E.g. Name on ID different from Bank Name", key="rf_notes")
        else:
            red_flags_notes = "None"
            
        reviewer_notes = st.text_area("Internal Notes", placeholder="General impression...", key="rev_notes")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back"):
            st.session_state.current_step = 2
            st.rerun()
    
    with col_next:
        if st.button("Generate Decision →", type="primary"):
            st.session_state.vendor_data.update({
                'responsiveness_rating': responsiveness_rating,
                'communication_quality': communication_quality,
                'red_flags_count': red_flags_count,
                'red_flags_notes': red_flags_notes,
                'reviewer_notes': reviewer_notes
            })
            
            # RUN LOGIC
            scorer = VendorScorerV3(st.session_state.vendor_data, mode=MODE)
            
            if MODE == "INITIAL":
                result = scorer.assess_initial_verification()
                st.session_state.final_result = result
            else:
                final_score = scorer.calculate_total_score()
                scorer.generate_recommendations()
                scorer.identify_risk_factors()
                badge_info = scorer.get_full_badge()
                st.session_state.final_result = {
                    'scorer': scorer,
                    'score': final_score,
                    'badge_info': badge_info,
                    'passed': final_score >= 60 # Arbitrary pass mark for full logic
                }
                
            st.session_state.current_step = 4
            st.rerun()

# ==========================================
# STEP 4: FINAL RESULT & CERTIFICATE
# ==========================================
elif st.session_state.current_step == 4:
    res = st.session_state.final_result
    data = st.session_state.vendor_data
    
    st.markdown(f'<div class="section-header"><h2>📊 Final Decision: {MODE}</h2></div>', unsafe_allow_html=True)

    # --- INITIAL MODE RESULT VIEW ---
    if MODE == "INITIAL":
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            <div class="metric-card-initial" style="background: {res['color']}">
                <div style="font-size: 2rem; font-weight: bold;">{res['badge']}</div>
                <div style="font-size: 1.2rem; margin-top: 10px;">{res['status']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if res['passed']:
                st.success("✅ Vendor has passed the Initial Trust Gate.")
                st.markdown("**Privileges Unlocked:**")
                st.markdown("- Can join WhatsApp Vendor Group")
                st.markdown("- Can post items for sale")
                st.markdown("- **Expiry:** 30 Days (Must do Full Verification by then)")
            else:
                st.error("❌ Verification Failed")
                st.markdown("**Reasons:**")
                for issue in res['issues']:
                    st.write(f"- {issue}")

        with col2:
            st.metric("Vendor", data['vendor_name'])
            st.caption(f"Location: {data['vendor_location']}")
            st.write(f"**Valid Until:** {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}")

    # --- FULL MODE RESULT VIEW ---
    else:
        scorer = res['scorer']
        badge = res['badge_info']
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="background: {badge['color']}">
                <div class="score-display">{res['score']}/100</div>
                <div style="font-size: 1.5rem;">{badge['badge']}</div>
                <div>{badge['status']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.write("**Risk Analysis**")
            if scorer.risk_factors:
                for risk in scorer.risk_factors:
                    st.write(f"- {risk}")
            else:
                st.write("No major risks found.")

    # --- CERTIFICATE GENERATION (DYNAMIC) ---
    st.markdown("---")
    st.markdown("### 📥 Download Certificate")
    
    # Logic for Certificate Content
    cert_title = "PROVISIONAL VENDOR PASS" if MODE == "INITIAL" else "CERTIFIED VENDOR LICENSE"
    cert_color = res['color'] if MODE == "INITIAL" else res['badge_info']['color']
    cert_status = res['status'] if MODE == "INITIAL" else res['badge_info']['status']
    
    # Hide score for Initial mode
    score_html = ""
    if MODE == "FULL":
        score_html = f'<div class="score-display">{res["score"]}/100</div>'
    
    validity_html = ""
    if MODE == "INITIAL":
        valid_date = (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')
        validity_html = f'<p style="color:red; font-weight:bold; margin-top:10px;">VALID UNTIL: {valid_date}</p>'

    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; padding: 20px; }}
            .container {{ border: 5px solid {cert_color}; padding: 30px; border-radius: 15px; text-align: center; }}
            .header {{ background: {cert_color}; color: white; padding: 15px; margin: -30px -30px 20px -30px; }}
            .vendor {{ font-size: 28px; font-weight: bold; text-transform: uppercase; margin: 20px 0; }}
            .badge {{ font-size: 24px; color: {cert_color}; font-weight: bold; border: 2px solid {cert_color}; padding: 10px 30px; border-radius: 50px; display: inline-block; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; border-top: 1px solid #ccc; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{cert_title}</h1>
                <p>Zolarux Trust Infrastructure</p>
            </div>
            <p>This certifies that</p>
            <div class="vendor">{data['vendor_name']}</div>
            <p>has undergone {MODE.lower()} verification checks.</p>
            <br>
            {score_html}
            <div class="badge">{cert_status}</div>
            {validity_html}
            <div class="footer">
                <p>Generated on {datetime.now().strftime('%Y-%m-%d')}</p>
                <p>ID: ZLX-{hash(data['vendor_name']) % 10000:04d}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    st.download_button(
        label="📄 Download Certificate",
        data=html_report,
        file_name=f"zolarux_{MODE.lower()}_cert_{data['vendor_name']}.html",
        mime="text/html"
    )

    if st.button("🔄 Start New"):
        st.session_state.current_step = 1
        st.session_state.vendor_data = {}
        st.rerun()
