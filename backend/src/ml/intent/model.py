"""Intent Transformer — small encoder model for trajectory prediction.

Architecture: Transformer encoder (4 layers, d_model=128, 4 heads) with
learned positional embeddings and dual output heads (position regression
+ action classification). ~1.7M parameters, trainable on CPU.
"""

import torch
import torch.nn as nn


class IntentTransformer(nn.Module):
    """Transformer encoder for player intent prediction.

    Input: (batch, seq_len=32, features=50) — preprocessed game state sequence
    Output: (position_deltas: (batch, 9), action_logits: (batch, 4))

    The model encodes a short history of player state and predicts:
    1. Where the player will be in +1s, +2s, +3s (9 regression targets)
    2. What tactical action they're performing (4 classification logits)
    """

    def __init__(
        self,
        input_dim: int = 50,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 4,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_seq_len: int = 32,
        num_position_targets: int = 9,
        num_action_classes: int = 4,
    ):
        """Initialize the model.

        Args:
            input_dim: Number of input features per tick
            d_model: Transformer hidden dimension
            nhead: Number of attention heads
            num_layers: Number of Transformer encoder layers
            dim_feedforward: Feed-forward hidden dimension
            dropout: Dropout rate
            max_seq_len: Maximum sequence length (for positional embedding)
            num_position_targets: Number of position regression outputs (9)
            num_action_classes: Number of action classes (4)
        """
        super().__init__()

        self.input_dim = input_dim
        self.d_model = d_model
        self.max_seq_len = max_seq_len

        # Input projection: raw features → d_model
        self.input_proj = nn.Linear(input_dim, d_model)

        # Learned positional embedding
        self.pos_embed = nn.Embedding(max_seq_len, d_model)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Output heads
        self.pos_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_position_targets),
        )

        self.action_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_action_classes),
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize linear layers with Xavier uniform, embeddings normal."""
        for name, param in self.named_parameters():
            if "weight" in name and param.dim() >= 2:
                nn.init.xavier_uniform_(param)
            elif "bias" in name:
                nn.init.zeros_(param)
            elif "pos_embed" in name:
                nn.init.normal_(param, mean=0.0, std=0.02)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.

        Args:
            x: (batch, seq_len, input_dim) input features

        Returns:
            (pos_deltas, action_logits) tuple where
            pos_deltas: (batch, 9) — predicted position deltas
            action_logits: (batch, 4) — action class logits
        """
        batch_size, seq_len, _ = x.shape

        # Project input
        x = self.input_proj(x)  # (B, S, d_model)

        # Add positional embeddings
        positions = torch.arange(seq_len, device=x.device).unsqueeze(0)  # (1, S)
        positions = positions.clamp(0, self.max_seq_len - 1)
        x = x + self.pos_embed(positions)  # (B, S, d_model)

        # Transformer encoder
        x = self.encoder(x)  # (B, S, d_model)

        # Extract output at last timestep
        last_hidden = x[:, -1, :]  # (B, d_model)

        # Dual heads
        pos_deltas = self.pos_head(last_hidden)  # (B, 9)
        action_logits = self.action_head(last_hidden)  # (B, 4)

        return pos_deltas, action_logits

    def predict(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Inference method — returns absolute positions and action probabilities.

        Args:
            x: (batch, seq_len, input_dim) input features

        Returns:
            (pos_deltas, action_probs, confidence) tuple
        """
        self.eval()
        with torch.no_grad():
            pos_deltas, action_logits = self.forward(x)
            action_probs = torch.softmax(action_logits, dim=-1)
            # Confidence from max action probability
            confidence = action_probs.max(dim=-1).values
        return pos_deltas, action_probs, confidence

    @property
    def num_params(self) -> int:
        """Total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def __repr__(self) -> str:
        return (
            f"IntentTransformer(input_dim={self.input_dim}, d_model={self.d_model}, "
            f"num_layers={self.encoder.num_layers}, params={self.num_params:,})"
        )
