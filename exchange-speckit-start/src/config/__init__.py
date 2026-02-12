"""
Config Manager - Policy and threat rules loading

Loads and manages policy configuration and threat rules from YAML files.
"""

import yaml
from typing import Dict, Any, Optional


class PolicyManager:
    """Manages policy configuration"""
    
    def __init__(self, policy_path: str = "./config/default_policy.yaml"):
        self.policy_path = policy_path
        self._policy = None
    
    def load_policy(self) -> Dict[str, Any]:
        """Load policy from YAML file"""
        if self._policy is not None:
            return self._policy
        
        try:
            with open(self.policy_path, 'r') as f:
                self._policy = yaml.safe_load(f)
            return self._policy
        except Exception:
            # Fallback to default policy
            return self._get_default_policy()
    
    def get_policy(self) -> Dict[str, Any]:
        """Get current policy"""
        return self.load_policy()
    
    def get_validation_gate(self, gate_id: str) -> Optional[Dict]:
        """Get specific validation gate configuration"""
        policy = self.get_policy()
        gates = policy.get('validation_gates', {})
        return gates.get(gate_id)
    
    def get_token_whitelist(self) -> list:
        """Get approved token list"""
        policy = self.get_policy()
        tokens = policy.get('token_whitelist', [])
        return [t['address'] for t in tokens if t.get('enabled', True)]
    
    def _get_default_policy(self) -> Dict[str, Any]:
        """Return default policy if file not available"""
        return {
            'max_slippage': 10.0,
            'min_confidence': 0.8,
            'validation_gates': {},
            'token_whitelist': []
        }


class ThreatRulesManager:
    """Manages threat rules configuration"""
    
    def __init__(self, rules_path: str = "./config/threat_rules.yaml"):
        self.rules_path = rules_path
        self._rules = None
    
    def load_threat_rules(self) -> Dict[str, Any]:
        """Load threat rules from YAML file"""
        if self._rules is not None:
            return self._rules
        
        try:
            with open(self.rules_path, 'r') as f:
                self._rules = yaml.safe_load(f)
            return self._rules
        except Exception:
            return self._get_default_rules()
    
    def get_threat_rules(self) -> Dict[str, Any]:
        """Get current threat rules"""
        return self.load_threat_rules()
    
    def get_threat_pattern(self, threat_code: str) -> Optional[Dict]:
        """Get threat pattern definition"""
        rules = self.get_threat_rules()
        threats = rules.get('threats', {})
        return threats.get(threat_code)
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Return default threat rules if file not available"""
        return {
            'threats': {},
            'detection': {'enabled': True},
            'response': {'default_rejection_message': 'Quote validation failed'}
        }
