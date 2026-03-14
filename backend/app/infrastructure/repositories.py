"""Реализация репозиториев с использованием SQLAlchemy."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import User
from app.domain.order import Order, OrderItem, OrderStatus, OrderStatusChange


class UserRepository:
    """Репозиторий для User."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # TODO: Реализовать save(user: User) -> None
    # Используйте INSERT ... ON CONFLICT DO UPDATE
    async def save(self, user: User) -> None:
        #raise NotImplementedError("TODO: Реализовать UserRepository.save")
        await self.session.execute(
            text("""
                INSERT INTO users (id, email, name, created_at)
                VALUES (:id, :email, :name, :created_at)
                ON CONFLICT (id) DO UPDATE
                SET email = EXCLUDED.email, name = EXCLUDED.name 
            """),
            {
                'id': str(user.id),
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at

            }
        )
        await self.session.commit()

    # TODO: Реализовать find_by_id(user_id: UUID) -> Optional[User]
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        #raise NotImplementedError("TODO: Реализовать UserRepository.find_by_id")
        result = await self.session.execute(
            text("""
                SELECT id, email, name, created_at FROM users WHERE id = :id
            """),
            {
                'id': str(user_id),
            }
        )
        row = result.fetchone()
        if row is None: return None
        return User(
            id = uuid.UUID(str(row[0])),
            email = row[1],
            name = row[2],
            created_at = row[3]
        )



    # TODO: Реализовать find_by_email(email: str) -> Optional[User]
    async def find_by_email(self, email: str) -> Optional[User]:
        #raise NotImplementedError("TODO: Реализовать UserRepository.find_by_email")
        result = await self.session.execute(
            text("""
                SELECT id, email, name, created_at FROM users WHERE email = :email
            """),
            {
                'email': email,
            }
        )
        row = result.fetchone()
        if row is None: return None
        return User(
            id = uuid.UUID(str(row[0])),
            email = row[1],
            name = row[2],
            created_at = row[3]
        )

    # TODO: Реализовать find_all() -> List[User]
    async def find_all(self) -> List[User]:
        #raise NotImplementedError("TODO: Реализовать UserRepository.find_all")
        result = await self.session.execute(
            text("""
                SELECT id, email, name, created_at FROM users
            """)
        )
        rows = result.fetchall()
        users = []
        for row in rows:
            users.append(
                User(
                    id = uuid.UUID(str(row[0])),
                    email = row[1],
                    name = row[2],
                    created_at = row[3]
                )
            )
        return users

class OrderRepository:
    """Репозиторий для Order."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # TODO: Реализовать save(order: Order) -> None
    # Сохранить заказ, товары и историю статусов
    async def save(self, order: Order) -> None:
        #raise NotImplementedError("TODO: Реализовать OrderRepository.save")
        await self.session.execute(
            text("""
                INSERT INTO orders (user_id, id, status, total_amount, created_at)
                VALUES (:user_id, :id, :status, :total_amount, :created_at)
                ON CONFLICT (id) DO UPDATE
                SET status = EXCLUDED.status, total_amount = EXCLUDED.total_amount
            """),
            {
                'user_id': str(order.user_id),
                'id': str(order.id),
                'status': order.status.value,
                'total_amount': order.total_amount,
                'created_at': order.created_at
            }
        )
        for item in order.items:
            await self.session.execute(
                text("""
                    INSERT INTO order_items (product_name, price, quantity, id, order_id)
                    VALUES (:product_name, :price, :quantity, :id, :order_id)
                    ON CONFLICT (id) DO UPDATE
                    SET product_name = EXCLUDED.product_name, price = EXCLUDED.price, quantity = EXCLUDED.quantity
                """),
                {
                    'product_name': item.product_name, 
                    'price': item.price, 
                    'quantity': item.quantity, 
                    'id': str(item.id), 
                    'order_id': str(item.order_id)
                }
            )
        for change in order.status_history:
            await self.session.execute(
                text("""
                    INSERT INTO order_status_history (order_id, status, changed_at, id)
                    VALUES (:order_id, :status, :changed_at, :id)
                    ON CONFLICT (id) DO UPDATE
                    SET  order_id = EXCLUDED.order_id
                """),
                {
                    'order_id': str(change.order_id), 
                    'status': change.status.value, 
                    'changed_at': change.changed_at, 
                    'id': str(change.id)
                }
            )
        await self.session.commit()


    # TODO: Реализовать find_by_id(order_id: UUID) -> Optional[Order]
    # Загрузить заказ со всеми товарами и историей
    # Используйте object.__new__(Order) чтобы избежать __post_init__
    async def find_by_id(self, order_id: uuid.UUID) -> Optional[Order]:
        #raise NotImplementedError("TODO: Реализовать OrderRepository.find_by_id")
        ord = await self.session.execute(
            text("SELECT id, user_id, status, total_amount, created_at FROM orders WHERE id = :id"),
            {'id': str(order_id)}
        )
        ord_id = ord.fetchone()
        if ord_id is None: return None
        
        ords = await self.session.execute(
            text("SELECT id, order_id, product_name, price, quantity FROM order_items WHERE order_id = :order_id"),
            {'order_id': str(order_id)}
        )
        rows = ords.fetchall()

        hist = await self.session.execute(
            text("SELECT id, order_id, status, changed_at FROM order_status_history WHERE order_id = :order_id"),
            {'order_id': str(order_id)}
        )
        history_rows = hist.fetchall()

        order = object.__new__(Order)
        order.id = uuid.UUID(str(ord_id[0]))
        order.user_id = uuid.UUID(str(ord_id[1]))
        order.status = OrderStatus(ord_id[2])
        order.total_amount = Decimal(str(ord_id[3]))
        order.created_at = ord_id[4]
        order.items = [
            OrderItem(
                id=uuid.UUID(str(row[0])),
                order_id=uuid.UUID(str(row[1])),
                product_name=row[2],
                price=Decimal(str(row[3])),
                quantity=row[4]
            )
            for row in rows
        ]
        order.status_history = [
            OrderStatusChange(
                id=uuid.UUID(str(row[0])),
                order_id=uuid.UUID(str(row[1])),
                status=OrderStatus(row[2]),
                changed_at=row[3]
            )
            for row in history_rows    
        ]

        return order


    # TODO: Реализовать find_by_user(user_id: UUID) -> List[Order]
    async def find_by_user(self, user_id: uuid.UUID) -> List[Order]:
        #raise NotImplementedError("TODO: Реализовать OrderRepository.find_by_user")
        usr = await self.session.execute(
            text("SELECT id, user_id, status, total_amount, created_at FROM orders WHERE user_id = :user_id"),
            {'user_id': str(user_id)}
        )
        order_rows = usr.fetchall()
        orders = []
        for ord_row in order_rows:
            ords = await self.session.execute(
                text("SELECT id, order_id, product_name, price, quantity FROM order_items WHERE order_id = :order_id"),
                {'order_id': str(ord_row[0])}
            )
            rows = ords.fetchall()
            hist = await self.session.execute(
                text("SELECT id, order_id, status, changed_at FROM order_status_history WHERE order_id = :order_id"),
                {'order_id': str(ord_row[0])}
            )
            history_rows = hist.fetchall()
            order = object.__new__(Order)
            order.id = uuid.UUID(str(ord_row[0]))
            order.user_id = uuid.UUID(str(ord_row[1]))
            order.status = OrderStatus(ord_row[2])
            order.total_amount = Decimal(str(ord_row[3]))
            order.created_at = ord_row[4]
            order.items = [
                OrderItem(
                    id=uuid.UUID(str(row[0])), 
                    order_id=uuid.UUID(str(row[1])), 
                    product_name=row[2], 
                    price=Decimal(str(row[3])), 
                    quantity=row[4]) 
                    for row in rows
                ]
            order.status_history = [
                OrderStatusChange(
                    id=uuid.UUID(str(row[0])), 
                    order_id=uuid.UUID(str(row[1])), 
                    status=OrderStatus(row[2]), 
                    changed_at=row[3]) 
                    for row in history_rows
                ]
            orders.append(order)
        return orders

    # TODO: Реализовать find_all() -> List[Order]
    async def find_all(self) -> List[Order]:
        #raise NotImplementedError("TODO: Реализовать OrderRepository.find_all")
        ord = await self.session.execute(
            text("SELECT id, user_id, status, total_amount, created_at FROM orders")
        )
        order_rows = ord.fetchall()
        orders = []
        for ord_row in order_rows:
            ords = await self.session.execute(
                text("SELECT id, order_id, product_name, price, quantity FROM order_items WHERE order_id = :order_id"),
                {'order_id': str(ord_row[0])}
            )
            rows = ords.fetchall()
            hist = await self.session.execute(
                text("SELECT id, order_id, status, changed_at FROM order_status_history WHERE order_id = :order_id"),
                {'order_id': str(ord_row[0])}
            )
            history_rows = hist.fetchall()
            order = object.__new__(Order)
            order.id = uuid.UUID(str(ord_row[0]))
            order.user_id = uuid.UUID(str(ord_row[1]))
            order.status = OrderStatus(ord_row[2])
            order.total_amount = Decimal(str(ord_row[3]))
            order.created_at = ord_row[4]
            order.items = [
                OrderItem(
                    id=uuid.UUID(str(row[0])), 
                    order_id=uuid.UUID(str(row[1])), 
                    product_name=row[2], 
                    price=Decimal(str(row[3])), 
                    quantity=row[4]) 
                    for row in rows
                ]
            order.status_history = [
                OrderStatusChange(
                    id=uuid.UUID(str(row[0])), 
                    order_id=uuid.UUID(str(row[1])), 
                    status=OrderStatus(row[2]), 
                    changed_at=row[3]) 
                    for row in history_rows
                ]
            orders.append(order)
        return orders
