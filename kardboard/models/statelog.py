from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    IntField,
    BooleanField,
)

from ..util import now, delta_in_hours


class StateLog(Document):
    card = StringField(required=True)
    """The card this record is for."""
    state = StringField(required=True)
    """The state the card was in for this record"""
    entered_at = DateTimeField(required=True)
    """Datetime the card entered its state"""
    exited_at = DateTimeField(required=False)
    """Datetime the card exited this state"""
    blocked = BooleanField(default=False)
    """Was this card ever blocked for the duration of this state record."""
    message = StringField(required=False)
    """A note about the state."""

    _blocked_at = DateTimeField(required=False)
    _unblocked_at = DateTimeField(required=False)
    _blocked_duration = IntField(required=False)
    _duration = IntField(required=False)
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)

    meta = {
        'cascade': False,
        'ordering': ['-created_at'],
        'indexes': ['card', 'state', ['card', 'created_at']]
    }

    def save(self, *args, **kwargs):
        if self.id is None:
            self.created_at = now()

        if not self.entered_at:
            self.entered_at = now()

        if self.entered_at and self.exited_at:
            self._duration = self.duration
        self.updated_at = now()
        super(StateLog, self).save(*args, **kwargs)

    def __repr__(self):
        return "<StateLog: %s, %s, %s -- %s, %s hours>" % (
            self.card.key,
            self.state,
            self.entered,
            self.exited,
            self._duration)

    @property
    def duration(self):
        if self._duration is not None:
            return self._duration

        if self.exited is not None:
            exited_at = self.exited_at
        else:
            exited_at = now()
        delta = exited_at - self.entered_at
        return delta_in_hours(delta)

    @property
    def as_dict(self):
        return {
            'card': self.card,
            'state': self.state,
            'entered_at': self.entered_at,
            'exited_at': self.exited_at,
            'blocked': self.blocked,
            'message': self.message,
        }
