"""
India Travel Infrastructure Database.
Comprehensive mapping of Indian cities to:
 - IATA airport codes
 - IRCTC station codes (primary station for each city)
 - City aliases / common misspellings
 - Approximate lat/lng for geocoding fallback

This ensures the system works for ALL Indian airports and railway stations
without relying on API resolution for every request.

Sources: DGCA, AAI, Indian Railways timetable data (public domain).
"""

from typing import Dict, List, Optional, Tuple

# ─── City → (IATA, StationCode, Latitude, Longitude) ─────────────────────────
# IATA: airport code (None if no commercial airport)
# StationCode: primary IRCTC station code
# Lat/Lng: city centre approximate

INDIA_CITIES: Dict[str, Dict] = {
    # ── Metro & Tier-1 ────────────────────────────────────────────────────────
    "delhi": {
        "iata": "DEL", "station": "NDLS",
        "lat": 28.6139, "lng": 77.2090,
        "state": "Delhi",
        "airport_name": "Indira Gandhi International Airport",
        "station_name": "New Delhi Railway Station",
    },
    "new delhi": {"iata": "DEL", "station": "NDLS", "lat": 28.6139, "lng": 77.2090, "state": "Delhi"},
    "mumbai": {
        "iata": "BOM", "station": "CSTM",
        "lat": 19.0760, "lng": 72.8777,
        "state": "Maharashtra",
        "airport_name": "Chhatrapati Shivaji Maharaj International Airport",
        "station_name": "Mumbai CSMT",
    },
    "bombay": {"iata": "BOM", "station": "CSTM", "lat": 19.0760, "lng": 72.8777, "state": "Maharashtra"},
    "bangalore": {
        "iata": "BLR", "station": "SBC",
        "lat": 12.9716, "lng": 77.5946,
        "state": "Karnataka",
        "airport_name": "Kempegowda International Airport",
        "station_name": "KSR Bengaluru City Junction",
    },
    "bengaluru": {"iata": "BLR", "station": "SBC", "lat": 12.9716, "lng": 77.5946, "state": "Karnataka"},
    "chennai": {
        "iata": "MAA", "station": "MAS",
        "lat": 13.0827, "lng": 80.2707,
        "state": "Tamil Nadu",
        "airport_name": "Chennai International Airport",
        "station_name": "Chennai Central",
    },
    "madras": {"iata": "MAA", "station": "MAS", "lat": 13.0827, "lng": 80.2707, "state": "Tamil Nadu"},
    "kolkata": {
        "iata": "CCU", "station": "KOAA",
        "lat": 22.5726, "lng": 88.3639,
        "state": "West Bengal",
        "airport_name": "Netaji Subhas Chandra Bose International Airport",
        "station_name": "Kolkata Station",
    },
    "calcutta": {"iata": "CCU", "station": "KOAA", "lat": 22.5726, "lng": 88.3639, "state": "West Bengal"},
    "hyderabad": {
        "iata": "HYD", "station": "SC",
        "lat": 17.3850, "lng": 78.4867,
        "state": "Telangana",
        "airport_name": "Rajiv Gandhi International Airport",
        "station_name": "Secunderabad Junction",
    },
    "pune": {
        "iata": "PNQ", "station": "PUNE",
        "lat": 18.5204, "lng": 73.8567,
        "state": "Maharashtra",
        "airport_name": "Pune Airport",
        "station_name": "Pune Junction",
    },
    "poona": {"iata": "PNQ", "station": "PUNE", "lat": 18.5204, "lng": 73.8567, "state": "Maharashtra"},
    "ahmedabad": {
        "iata": "AMD", "station": "ADI",
        "lat": 23.0225, "lng": 72.5714,
        "state": "Gujarat",
        "airport_name": "Sardar Vallabhbhai Patel International Airport",
        "station_name": "Ahmedabad Junction",
    },
    "amdavad": {"iata": "AMD", "station": "ADI", "lat": 23.0225, "lng": 72.5714, "state": "Gujarat"},

    # ── Tier-2 with airports ──────────────────────────────────────────────────
    "goa": {
        "iata": "GOI", "station": "MAO",
        "lat": 15.2993, "lng": 74.1240,
        "state": "Goa",
        "airport_name": "Goa International Airport (Dabolim)",
        "station_name": "Madgaon Junction",
    },
    "panaji": {"iata": "GOI", "station": "MAO", "lat": 15.4909, "lng": 73.8278, "state": "Goa"},
    "jaipur": {
        "iata": "JAI", "station": "JP",
        "lat": 26.9124, "lng": 75.7873,
        "state": "Rajasthan",
        "airport_name": "Jaipur International Airport",
        "station_name": "Jaipur Junction",
    },
    "lucknow": {
        "iata": "LKO", "station": "LKO",
        "lat": 26.8467, "lng": 80.9462,
        "state": "Uttar Pradesh",
        "airport_name": "Chaudhary Charan Singh International Airport",
        "station_name": "Lucknow Junction",
    },
    "kochi": {
        "iata": "COK", "station": "ERS",
        "lat": 9.9312, "lng": 76.2673,
        "state": "Kerala",
        "airport_name": "Cochin International Airport",
        "station_name": "Ernakulam Junction",
    },
    "cochin": {"iata": "COK", "station": "ERS", "lat": 9.9312, "lng": 76.2673, "state": "Kerala"},
    "ernakulam": {"iata": "COK", "station": "ERS", "lat": 9.9312, "lng": 76.2673, "state": "Kerala"},
    "chandigarh": {
        "iata": "IXC", "station": "CDG",
        "lat": 30.7333, "lng": 76.7794,
        "state": "Punjab",
        "airport_name": "Chandigarh International Airport",
        "station_name": "Chandigarh Railway Station",
    },
    "amritsar": {
        "iata": "ATQ", "station": "ASR",
        "lat": 31.6340, "lng": 74.8723,
        "state": "Punjab",
        "airport_name": "Sri Guru Ram Dass Jee International Airport",
        "station_name": "Amritsar Junction",
    },
    "varanasi": {
        "iata": "VNS", "station": "BSB",
        "lat": 25.3176, "lng": 82.9739,
        "state": "Uttar Pradesh",
        "airport_name": "Lal Bahadur Shastri International Airport",
        "station_name": "Varanasi Junction",
    },
    "banaras": {"iata": "VNS", "station": "BSB", "lat": 25.3176, "lng": 82.9739, "state": "Uttar Pradesh"},
    "benares": {"iata": "VNS", "station": "BSB", "lat": 25.3176, "lng": 82.9739, "state": "Uttar Pradesh"},
    "kashi":   {"iata": "VNS", "station": "BSB", "lat": 25.3176, "lng": 82.9739, "state": "Uttar Pradesh"},
    "nagpur": {
        "iata": "NAG", "station": "NGP",
        "lat": 21.1458, "lng": 79.0882,
        "state": "Maharashtra",
        "airport_name": "Dr. Babasaheb Ambedkar International Airport",
        "station_name": "Nagpur Junction",
    },
    "surat": {
        "iata": "STV", "station": "ST",
        "lat": 21.1702, "lng": 72.8311,
        "state": "Gujarat",
        "airport_name": "Surat Airport",
        "station_name": "Surat Railway Station",
    },
    "indore": {
        "iata": "IDR", "station": "INDB",
        "lat": 22.7196, "lng": 75.8577,
        "state": "Madhya Pradesh",
        "airport_name": "Devi Ahilya Bai Holkar Airport",
        "station_name": "Indore Junction",
    },
    "bhopal": {
        "iata": "BHO", "station": "BPL",
        "lat": 23.2599, "lng": 77.4126,
        "state": "Madhya Pradesh",
        "airport_name": "Raja Bhoj Airport",
        "station_name": "Bhopal Junction",
    },
    "visakhapatnam": {
        "iata": "VTZ", "station": "VSKP",
        "lat": 17.6868, "lng": 83.2185,
        "state": "Andhra Pradesh",
        "airport_name": "Visakhapatnam Airport",
        "station_name": "Visakhapatnam Railway Station",
    },
    "vizag": {"iata": "VTZ", "station": "VSKP", "lat": 17.6868, "lng": 83.2185, "state": "Andhra Pradesh"},
    "coimbatore": {
        "iata": "CJB", "station": "CBE",
        "lat": 11.0168, "lng": 76.9558,
        "state": "Tamil Nadu",
        "airport_name": "Coimbatore International Airport",
        "station_name": "Coimbatore Junction",
    },
    "madurai": {
        "iata": "IXM", "station": "MDU",
        "lat": 9.9252, "lng": 78.1198,
        "state": "Tamil Nadu",
        "airport_name": "Madurai Airport",
        "station_name": "Madurai Junction",
    },
    "trichy": {
        "iata": "TRZ", "station": "TPJ",
        "lat": 10.7905, "lng": 78.7047,
        "state": "Tamil Nadu",
        "airport_name": "Tiruchirappalli International Airport",
        "station_name": "Tiruchirappalli Junction",
    },
    "tiruchirappalli": {"iata": "TRZ", "station": "TPJ", "lat": 10.7905, "lng": 78.7047, "state": "Tamil Nadu"},
    "patna": {
        "iata": "PAT", "station": "PNBE",
        "lat": 25.5941, "lng": 85.1376,
        "state": "Bihar",
        "airport_name": "Jay Prakash Narayan Airport",
        "station_name": "Patna Junction",
    },
    "ranchi": {
        "iata": "IXR", "station": "RNC",
        "lat": 23.3441, "lng": 85.3096,
        "state": "Jharkhand",
        "airport_name": "Birsa Munda Airport",
        "station_name": "Ranchi Railway Station",
    },
    "bhubaneswar": {
        "iata": "BBI", "station": "BBS",
        "lat": 20.2961, "lng": 85.8245,
        "state": "Odisha",
        "airport_name": "Biju Patnaik International Airport",
        "station_name": "Bhubaneswar Railway Station",
    },
    "guwahati": {
        "iata": "GAU", "station": "GHY",
        "lat": 26.1445, "lng": 91.7362,
        "state": "Assam",
        "airport_name": "Lokpriya Gopinath Bordoloi International Airport",
        "station_name": "Guwahati Railway Station",
    },
    "thiruvananthapuram": {
        "iata": "TRV", "station": "TVC",
        "lat": 8.5241, "lng": 76.9366,
        "state": "Kerala",
        "airport_name": "Trivandrum International Airport",
        "station_name": "Thiruvananthapuram Central",
    },
    "trivandrum": {"iata": "TRV", "station": "TVC", "lat": 8.5241, "lng": 76.9366, "state": "Kerala"},
    "kozhikode": {
        "iata": "CCJ", "station": "CLT",
        "lat": 11.2588, "lng": 75.7804,
        "state": "Kerala",
        "airport_name": "Calicut International Airport",
        "station_name": "Kozhikode Railway Station",
    },
    "calicut": {"iata": "CCJ", "station": "CLT", "lat": 11.2588, "lng": 75.7804, "state": "Kerala"},
    "mangalore": {
        "iata": "IXE", "station": "MAJN",
        "lat": 12.9141, "lng": 74.8560,
        "state": "Karnataka",
        "airport_name": "Mangaluru International Airport",
        "station_name": "Mangaluru Junction",
    },
    "hubli": {
        "iata": "HBX", "station": "UBL",
        "lat": 15.3647, "lng": 75.1240,
        "state": "Karnataka",
        "airport_name": "Hubballi Airport",
        "station_name": "Hubballi Junction",
    },
    "mysore": {
        "iata": "MYQ", "station": "MYS",
        "lat": 12.2958, "lng": 76.6394,
        "state": "Karnataka",
        "airport_name": "Mysore Airport",
        "station_name": "Mysuru Junction",
    },
    "mysuru": {"iata": "MYQ", "station": "MYS", "lat": 12.2958, "lng": 76.6394, "state": "Karnataka"},
    "vadodara": {
        "iata": "BDQ", "station": "BRC",
        "lat": 22.3072, "lng": 73.1812,
        "state": "Gujarat",
        "airport_name": "Vadodara Airport",
        "station_name": "Vadodara Junction",
    },
    "baroda": {"iata": "BDQ", "station": "BRC", "lat": 22.3072, "lng": 73.1812, "state": "Gujarat"},
    "rajkot": {
        "iata": "RAJ", "station": "RJT",
        "lat": 22.3039, "lng": 70.8022,
        "state": "Gujarat",
        "airport_name": "Rajkot Airport",
        "station_name": "Rajkot Junction",
    },
    "jodhpur": {
        "iata": "JDH", "station": "JU",
        "lat": 26.2389, "lng": 73.0243,
        "state": "Rajasthan",
        "airport_name": "Jodhpur Airport",
        "station_name": "Jodhpur Junction",
    },
    "udaipur": {
        "iata": "UDR", "station": "UDZ",
        "lat": 24.5854, "lng": 73.7125,
        "state": "Rajasthan",
        "airport_name": "Maharana Pratap Airport",
        "station_name": "Udaipur City",
    },
    "agra": {
        "iata": "AGR", "station": "AF",
        "lat": 27.1767, "lng": 78.0081,
        "state": "Uttar Pradesh",
        "airport_name": "Agra Airport",
        "station_name": "Agra Fort",
    },
    "dehradun": {
        "iata": "DED", "station": "DDN",
        "lat": 30.3165, "lng": 78.0322,
        "state": "Uttarakhand",
        "airport_name": "Jolly Grant Airport",
        "station_name": "Dehradun Railway Station",
    },
    "srinagar": {
        "iata": "SXR", "station": "JAT",
        "lat": 34.0837, "lng": 74.7973,
        "state": "Jammu & Kashmir",
        "airport_name": "Sheikh ul-Alam International Airport",
        "station_name": "Jammu Tawi (nearest railhead)",
    },
    "jammu": {
        "iata": "IXJ", "station": "JAT",
        "lat": 32.7266, "lng": 74.8570,
        "state": "Jammu & Kashmir",
        "airport_name": "Jammu Airport",
        "station_name": "Jammu Tawi",
    },
    "leh": {
        "iata": "IXL", "station": None,
        "lat": 34.1526, "lng": 77.5771,
        "state": "Ladakh",
        "airport_name": "Kushok Bakula Rimpochhe Airport",
        "station_name": None,
    },
    "ladakh": {"iata": "IXL", "station": None, "lat": 34.1526, "lng": 77.5771, "state": "Ladakh"},
    "shimla": {
        "iata": "SLV", "station": "SML",
        "lat": 31.1048, "lng": 77.1734,
        "state": "Himachal Pradesh",
        "airport_name": "Shimla Airport",
        "station_name": "Shimla Railway Station",
    },
    "manali": {
        "iata": "KUU", "station": None,
        "lat": 32.2396, "lng": 77.1887,
        "state": "Himachal Pradesh",
        "airport_name": "Kullu-Manali Airport (Bhuntar)",
        "station_name": None,
    },
    "darjeeling": {
        "iata": "GAY", "station": "NJP",
        "lat": 27.0360, "lng": 88.2627,
        "state": "West Bengal",
        "airport_name": "Bagdogra Airport (nearest)",
        "station_name": "New Jalpaiguri (nearest)",
    },
    "gangtok": {
        "iata": "PYG", "station": "NJP",
        "lat": 27.3389, "lng": 88.6065,
        "state": "Sikkim",
        "airport_name": "Pakyong Airport",
        "station_name": "New Jalpaiguri (nearest railhead)",
    },
    "siliguri": {
        "iata": "IXB", "station": "NJP",
        "lat": 26.7271, "lng": 88.3953,
        "state": "West Bengal",
        "airport_name": "Bagdogra Airport",
        "station_name": "New Jalpaiguri",
    },
    "raipur": {
        "iata": "RPR", "station": "R",
        "lat": 21.2514, "lng": 81.6296,
        "state": "Chhattisgarh",
        "airport_name": "Swami Vivekananda Airport",
        "station_name": "Raipur Junction",
    },
    "nashik": {
        "iata": "ISK", "station": "NK",
        "lat": 19.9975, "lng": 73.7898,
        "state": "Maharashtra",
        "airport_name": "Ozar Airport",
        "station_name": "Nashik Road",
    },
    "aurangabad": {
        "iata": "IXU", "station": "AWB",
        "lat": 19.8762, "lng": 75.3433,
        "state": "Maharashtra",
        "airport_name": "Aurangabad Airport",
        "station_name": "Aurangabad Railway Station",
    },
    "kolhapur": {
        "iata": "KLH", "station": "KOP",
        "lat": 16.7050, "lng": 74.2433,
        "state": "Maharashtra",
        "airport_name": "Kolhapur Airport",
        "station_name": "Kolhapur Railway Station",
    },
    "port blair": {
        "iata": "IXZ", "station": None,
        "lat": 11.6234, "lng": 92.7265,
        "state": "Andaman & Nicobar",
        "airport_name": "Veer Savarkar International Airport",
        "station_name": None,
    },
    "andaman": {"iata": "IXZ", "station": None, "lat": 11.6234, "lng": 92.7265, "state": "Andaman & Nicobar"},
    "imphal": {
        "iata": "IMF", "station": None,
        "lat": 24.8170, "lng": 93.9368,
        "state": "Manipur",
        "airport_name": "Bir Tikendrajit International Airport",
        "station_name": None,
    },
    "aizawl": {
        "iata": "AJL", "station": None,
        "lat": 23.7307, "lng": 92.7173,
        "state": "Mizoram",
        "airport_name": "Lengpui Airport",
        "station_name": None,
    },
    "agartala": {
        "iata": "IXA", "station": "AGTL",
        "lat": 23.8315, "lng": 91.2868,
        "state": "Tripura",
        "airport_name": "Maharaja Bir Bikram Airport",
        "station_name": "Agartala Railway Station",
    },
    "dibrugarh": {
        "iata": "DIB", "station": "DBRG",
        "lat": 27.4728, "lng": 94.9120,
        "state": "Assam",
        "airport_name": "Dibrugarh Airport",
        "station_name": "Dibrugarh Town",
    },
    "haridwar": {
        "iata": None, "station": "HW",
        "lat": 29.9457, "lng": 78.1642,
        "state": "Uttarakhand",
        "airport_name": None,
        "station_name": "Haridwar Junction",
    },
    "rishikesh": {
        "iata": None, "station": "RKSH",
        "lat": 30.0869, "lng": 78.2676,
        "state": "Uttarakhand",
        "airport_name": None,
        "station_name": "Rishikesh Railway Station",
    },
    "puri": {
        "iata": None, "station": "PURI",
        "lat": 19.8135, "lng": 85.8312,
        "state": "Odisha",
        "airport_name": None,
        "station_name": "Puri Railway Station",
    },
    "mathura": {
        "iata": None, "station": "MTJ",
        "lat": 27.4924, "lng": 77.6737,
        "state": "Uttar Pradesh",
        "airport_name": None,
        "station_name": "Mathura Junction",
    },
    "allahabad": {
        "iata": "IXD", "station": "ALD",
        "lat": 25.4358, "lng": 81.8463,
        "state": "Uttar Pradesh",
        "airport_name": "Prayagraj Airport",
        "station_name": "Allahabad Junction",
    },
    "prayagraj": {"iata": "IXD", "station": "ALD", "lat": 25.4358, "lng": 81.8463, "state": "Uttar Pradesh"},
    "gorakhpur": {
        "iata": "GOP", "station": "GKP",
        "lat": 26.7606, "lng": 83.3732,
        "state": "Uttar Pradesh",
        "airport_name": "Gorakhpur Airport",
        "station_name": "Gorakhpur Junction",
    },
    "kanpur": {
        "iata": "KNU", "station": "CNB",
        "lat": 26.4499, "lng": 80.3319,
        "state": "Uttar Pradesh",
        "airport_name": "Kanpur Airport",
        "station_name": "Kanpur Central",
    },
    "meerut": {
        "iata": None, "station": "MTC",
        "lat": 28.9845, "lng": 77.7064,
        "state": "Uttar Pradesh",
        "airport_name": None,
        "station_name": "Meerut City",
    },
    "ludhiana": {
        "iata": "LUH", "station": "LDH",
        "lat": 30.9010, "lng": 75.8573,
        "state": "Punjab",
        "airport_name": "Sahnewal Airport",
        "station_name": "Ludhiana Junction",
    },
    "jalandhar": {
        "iata": None, "station": "JUC",
        "lat": 31.3260, "lng": 75.5762,
        "state": "Punjab",
        "airport_name": None,
        "station_name": "Jalandhar City",
    },
    "bikaner": {
        "iata": "BKB", "station": "BKN",
        "lat": 28.0229, "lng": 73.3119,
        "state": "Rajasthan",
        "airport_name": "Nal Airport",
        "station_name": "Bikaner Junction",
    },
    "ajmer": {
        "iata": None, "station": "AII",
        "lat": 26.4521, "lng": 74.6382,
        "state": "Rajasthan",
        "airport_name": None,
        "station_name": "Ajmer Junction",
    },
    "kota": {
        "iata": None, "station": "KOTA",
        "lat": 25.2138, "lng": 75.8648,
        "state": "Rajasthan",
        "airport_name": None,
        "station_name": "Kota Junction",
    },
    "gwalior": {
        "iata": "GWL", "station": "GWL",
        "lat": 26.2183, "lng": 78.1828,
        "state": "Madhya Pradesh",
        "airport_name": "Rajmata Vijaya Raje Scindia Air Terminal",
        "station_name": "Gwalior Junction",
    },
    "jabalpur": {
        "iata": "JLR", "station": "JBP",
        "lat": 23.1815, "lng": 79.9864,
        "state": "Madhya Pradesh",
        "airport_name": "Dumna Airport",
        "station_name": "Jabalpur Junction",
    },
    "jamshedpur": {
        "iata": None, "station": "TATA",
        "lat": 22.8046, "lng": 86.2029,
        "state": "Jharkhand",
        "airport_name": None,
        "station_name": "Tatanagar Junction",
    },
    "durgapur": {
        "iata": "RDP", "station": "DGR",
        "lat": 23.4800, "lng": 87.3200,
        "state": "West Bengal",
        "airport_name": "Kazi Nazrul Islam Airport",
        "station_name": "Durgapur Railway Station",
    },
    "vijayawada": {
        "iata": "VGA", "station": "BZA",
        "lat": 16.5062, "lng": 80.6480,
        "state": "Andhra Pradesh",
        "airport_name": "Vijayawada Airport",
        "station_name": "Vijayawada Junction",
    },
    "tirupati": {
        "iata": "TIR", "station": "TPTY",
        "lat": 13.6288, "lng": 79.4192,
        "state": "Andhra Pradesh",
        "airport_name": "Tirupati Airport",
        "station_name": "Tirupati Railway Station",
    },
    "nellore": {
        "iata": None, "station": "NLR",
        "lat": 14.4426, "lng": 79.9865,
        "state": "Andhra Pradesh",
        "airport_name": None,
        "station_name": "Nellore Railway Station",
    },
    "warangal": {
        "iata": None, "station": "WL",
        "lat": 17.9784, "lng": 79.5941,
        "state": "Telangana",
        "airport_name": None,
        "station_name": "Warangal Railway Station",
    },
    "salem": {
        "iata": "SXV", "station": "SA",
        "lat": 11.6643, "lng": 78.1460,
        "state": "Tamil Nadu",
        "airport_name": "Salem Airport",
        "station_name": "Salem Junction",
    },
    "ooty": {
        "iata": None, "station": "UAM",
        "lat": 11.4064, "lng": 76.6932,
        "state": "Tamil Nadu",
        "airport_name": None,
        "station_name": "Udagamandalam (Ooty)",
    },
    "vellore": {
        "iata": None, "station": "VLR",
        "lat": 12.9165, "lng": 79.1325,
        "state": "Tamil Nadu",
        "airport_name": None,
        "station_name": "Vellore",
    },
    "pondicherry": {
        "iata": "PNY", "station": "PDY",
        "lat": 11.9416, "lng": 79.8083,
        "state": "Puducherry",
        "airport_name": "Pondicherry Airport",
        "station_name": "Puducherry Railway Station",
    },
    "puducherry": {"iata": "PNY", "station": "PDY", "lat": 11.9416, "lng": 79.8083, "state": "Puducherry"},
    "thrissur": {
        "iata": None, "station": "TCR",
        "lat": 10.5276, "lng": 76.2144,
        "state": "Kerala",
        "airport_name": None,
        "station_name": "Thrissur Railway Station",
    },
    "palakkad": {
        "iata": None, "station": "PGT",
        "lat": 10.7867, "lng": 76.6548,
        "state": "Kerala",
        "airport_name": None,
        "station_name": "Palakkad Junction",
    },
}

# ─── Alias resolution ────────────────────────────────────────────────────────

CITY_ALIASES: Dict[str, str] = {
    "delhii": "delhi",   "dilhi": "delhi",    "dilli": "delhi",
    "new dhelhi": "new delhi",
    "mumabi": "mumbai",  "mumbay": "mumbai",   "mumbaa": "mumbai",
    "banglore": "bangalore", "bangalor": "bangalore", "bangluru": "bangalore",
    "bengaluru": "bangalore", "blr": "bangalore",
    "ahemdabad": "ahmedabad", "ahmedabd": "ahmedabad", "amdavad": "ahmedabad",
    "punne": "pune",     "poona": "pune",      "puna": "pune",
    "hydrabad": "hyderabad", "hyderabad": "hyderabad", "hyd": "hyderabad",
    "secunderabad": "hyderabad",
    "chenai": "chennai", "chennaai": "chennai",
    "kolkatta": "kolkata", "calcuta": "kolkata", "kolkota": "kolkata",
    "jaipure": "jaipur", "pinkcity": "jaipur",
    "trivandum": "trivandrum", "tvm": "trivandrum",
    "lko": "lucknow",
    "vizag": "visakhapatnam",
    "blore": "bangalore",
    "bom": "mumbai",     "del": "delhi",       "ccu": "kolkata",
    "maa": "chennai",    "hyd": "hyderabad",
}


def resolve_city(raw: str) -> Optional[Dict]:
    """
    Resolve a raw city name string to its canonical city data dict.
    Returns None if not found.
    """
    if not raw:
        return None
    normalized = raw.strip().lower()

    # Direct lookup
    if normalized in INDIA_CITIES:
        return {**INDIA_CITIES[normalized], "city": normalized}

    # Alias lookup
    canonical = CITY_ALIASES.get(normalized)
    if canonical and canonical in INDIA_CITIES:
        return {**INDIA_CITIES[canonical], "city": canonical}

    # Fuzzy: find a city that starts with the input
    for city_key, data in INDIA_CITIES.items():
        if city_key.startswith(normalized) or normalized.startswith(city_key):
            return {**data, "city": city_key}

    return None


def get_iata(city: str) -> Optional[str]:
    data = resolve_city(city)
    return data.get("iata") if data else None


def get_station_code(city: str) -> Optional[str]:
    data = resolve_city(city)
    return data.get("station") if data else None


def get_city_coords(city: str) -> Optional[Tuple[float, float]]:
    data = resolve_city(city)
    if data and data.get("lat") and data.get("lng"):
        return data["lat"], data["lng"]
    return None


def get_all_cities() -> List[str]:
    return sorted(set(list(INDIA_CITIES.keys()) + list(CITY_ALIASES.keys())))
