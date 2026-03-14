"""Доменные сущности заказа."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from .exceptions import (
    OrderAlreadyPaidError,
    OrderCancelledError,
    InvalidQuantityError,
    InvalidPriceError,
    InvalidAmountError,
)

from dataclasses import dataclass, field


# TODO: Реализовать OrderStatus (str, Enum)
# Значения: CREATED, PAID, CANCELLED, SHIPPED, COMPLETED
class OrderStatus(str, Enum):
    CREATED = 'CREATED'
    PAID = 'PAID'
    CANCELLED = 'CANCELLED'
    SHIPPED = 'SHIPPED'
    COMPLETED = 'COMPLETED'


# TODO: Реализовать OrderItem (dataclass)
# Поля: product_name, price, quantity, id, order_id
# Свойство: subtotal (price * quantity)
# Валидация: quantity > 0, price >= 0
@dataclass
class OrderItem:
    product_name: str
    price: Decimal
    quantity: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    order_id: Optional[uuid.UUID] = None

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity

    def __post_init__(self):
        if self.quantity <= 0:
            raise InvalidQuantityError(self.quantity)
        if self.price < 0:
            raise InvalidPriceError(self.price)
    


# TODO: Реализовать OrderStatusChange (dataclass)
# Поля: order_id, status, changed_at, id
@dataclass
class OrderStatusChange:
    order_id: uuid.UUID
    status: OrderStatus
    changed_at: datetime = field(default_factory=datetime.utcnow)
    id: uuid.UUID = field(default_factory=uuid.uuid4)

# TODO: Реализовать Order (dataclass)
# Поля: user_id, id, status, total_amount, created_at, items, status_history
# Методы:
#   - add_item(product_name, price, quantity) -> OrderItem
#   - pay() -> None  [КРИТИЧНО: нельзя оплатить дважды!]
#   - cancel() -> None
#   - ship() -> None
#   - complete() -> None
@dataclass
class Order:
    user_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: OrderStatus = OrderStatus.CREATED
    total_amount: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    items: List[OrderItem] = field(default_factory=list)
    status_history: List[OrderStatusChange] = field(default_factory=list)

    def add_item(self, product_name: str, price: Decimal, quantity: int) -> OrderItem:
        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id)
        order_item = OrderItem(
            product_name=product_name,
            price=price,
            quantity=quantity,
            order_id=self.id
        )
        new_total_amount = self.total_amount + order_item.subtotal
        if new_total_amount < 0:
            raise InvalidAmountError(new_total_amount)
        self.items.append(order_item)
        self.total_amount = new_total_amount
        return order_item

    
    def pay(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)
        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id)
        self.status = OrderStatus.PAID
        self.status_history.append(OrderStatusChange(order_id=self.id, status=OrderStatus.PAID))

    def cancel(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)
        self.status = OrderStatus.CANCELLED
        self.status_history.append(OrderStatusChange(order_id=self.id, status=OrderStatus.CANCELLED))

    def ship(self) -> None:
        if self.status != OrderStatus.PAID:
            raise ValueError()
        self.status = OrderStatus.SHIPPED
        self.status_history.append(OrderStatusChange(order_id=self.id, status=OrderStatus.SHIPPED))

    def complete(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise ValueError()
        self.status = OrderStatus.COMPLETED
        self.status_history.append(OrderStatusChange(order_id=self.id, status=OrderStatus.COMPLETED))
