from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import ChatMessage, BlockedUser, ChatRequest, DirectMessageThread, DirectMessage

User = get_user_model()


class ChatMessageModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_create_message(self):
        msg = ChatMessage.objects.create(user=self.user, text='Hello world')
        self.assertEqual(msg.text, 'Hello world')
        self.assertEqual(msg.user, self.user)
        self.assertIsNotNone(msg.created_at)

    def test_message_ordering(self):
        msg1 = ChatMessage.objects.create(user=self.user, text='First')
        msg2 = ChatMessage.objects.create(user=self.user, text='Second')
        messages = list(ChatMessage.objects.all())
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)


class ChatViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='chatuser', password='pass')

    def test_chat_view_requires_login(self):
        response = self.client.get(reverse('chat_interno:chat'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_chat_view_accessible_when_logged_in(self):
        self.client.login(username='chatuser', password='pass')
        response = self.client.get(reverse('chat_interno:chat'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chat del mercado')


class MessagesApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='pass')
        self.client.login(username='apiuser', password='pass')

    def test_messages_api_returns_empty_list(self):
        response = self.client.get(reverse('chat_interno:messages-api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['messages'], [])

    def test_messages_api_returns_messages(self):
        ChatMessage.objects.create(user=self.user, text='Test message 1')
        ChatMessage.objects.create(user=self.user, text='Test message 2')
        response = self.client.get(reverse('chat_interno:messages-api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['messages']), 2)
        self.assertEqual(data['messages'][0]['text'], 'Test message 1')
        self.assertEqual(data['messages'][1]['text'], 'Test message 2')

    def test_messages_api_filters_by_after_id(self):
        msg1 = ChatMessage.objects.create(user=self.user, text='Message 1')
        ChatMessage.objects.create(user=self.user, text='Message 2')
        response = self.client.get(reverse('chat_interno:messages-api') + f'?after_id={msg1.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['text'], 'Message 2')

    def test_messages_api_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('chat_interno:messages-api'))
        self.assertEqual(response.status_code, 302)


class PostMessageApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='poster', password='pass')
        self.client.login(username='poster', password='pass')

    def test_post_message_creates_message(self):
        response = self.client.post(
            reverse('chat_interno:post-api'),
            {'text': 'New message'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('created_at', data)
        self.assertEqual(ChatMessage.objects.count(), 1)
        msg = ChatMessage.objects.first()
        self.assertEqual(msg.text, 'New message')
        self.assertEqual(msg.user, self.user)

    def test_post_message_rejects_empty_text(self):
        response = self.client.post(
            reverse('chat_interno:post-api'),
            {'text': '   '}
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'empty')
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_post_message_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('chat_interno:post-api'),
            {'text': 'Test'}
        )
        self.assertEqual(response.status_code, 302)

    def test_post_message_requires_post_method(self):
        response = self.client.get(reverse('chat_interno:post-api'))
        self.assertEqual(response.status_code, 405)


class BlockedUserModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')

    def test_create_block(self):
        block = BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        self.assertEqual(block.blocker, self.user1)
        self.assertEqual(block.blocked, self.user2)
        self.assertIsNotNone(block.created_at)

    def test_unique_block_constraint(self):
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        with self.assertRaises(Exception):
            BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)


class ChatRequestModelTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username='requester', password='pass')
        self.target = User.objects.create_user(username='target', password='pass')

    def test_create_request(self):
        req = ChatRequest.objects.create(requester=self.requester, target=self.target)
        self.assertEqual(req.status, ChatRequest.STATUS_REQUESTED)
        self.assertIsNone(req.responded_at)

    def test_accept_request(self):
        req = ChatRequest.objects.create(requester=self.requester, target=self.target)
        req.accept()
        req.refresh_from_db()
        self.assertEqual(req.status, ChatRequest.STATUS_ACCEPTED)
        self.assertIsNotNone(req.responded_at)

    def test_decline_request(self):
        req = ChatRequest.objects.create(requester=self.requester, target=self.target)
        req.decline()
        req.refresh_from_db()
        self.assertEqual(req.status, ChatRequest.STATUS_DECLINED)
        self.assertIsNotNone(req.responded_at)

    def test_accept_only_works_on_requested(self):
        req = ChatRequest.objects.create(requester=self.requester, target=self.target)
        req.decline()
        req.refresh_from_db()
        old_status = req.status
        req.accept()
        req.refresh_from_db()
        self.assertEqual(req.status, old_status)

    def test_unique_pending_constraint(self):
        ChatRequest.objects.create(requester=self.requester, target=self.target, status=ChatRequest.STATUS_REQUESTED)
        with self.assertRaises(Exception):
            ChatRequest.objects.create(requester=self.requester, target=self.target, status=ChatRequest.STATUS_REQUESTED)


class BlockingViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.client.login(username='user1', password='pass')

    def test_block_user_creates_block(self):
        response = self.client.post(reverse('chat_interno:block-user', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BlockedUser.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_unblock_user_removes_block(self):
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.post(reverse('chat_interno:unblock-user', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BlockedUser.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_blocked_list_shows_blocked_users(self):
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.get(reverse('chat_interno:blocked-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user2.username)

    def test_blocking_prevents_private_start(self):
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.get(reverse('chat_interno:private-start', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DirectMessageThread.objects.filter(user1=self.user1, user2=self.user2).exists())
        self.assertFalse(DirectMessageThread.objects.filter(user1=self.user2, user2=self.user1).exists())

    def test_blocking_prevents_private_chat_access(self):
        a, b = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        thread = DirectMessageThread.objects.create(user1=a, user2=b)
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.get(reverse('chat_interno:private-chat', args=[thread.id]))
        self.assertEqual(response.status_code, 403)

    def test_blocking_prevents_sending_messages(self):
        a, b = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        thread = DirectMessageThread.objects.create(user1=a, user2=b)
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.post(
            reverse('chat_interno:private-post', args=[thread.id]),
            {'text': 'This should fail'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(DirectMessage.objects.count(), 0)

    def test_blocking_prevents_reading_messages(self):
        a, b = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        thread = DirectMessageThread.objects.create(user1=a, user2=b)
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.get(reverse('chat_interno:private-messages', args=[thread.id]))
        self.assertEqual(response.status_code, 403)


class ChatRequestViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.client.login(username='user1', password='pass')

    def test_send_request_creates_request(self):
        response = self.client.post(reverse('chat_interno:request-send', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ChatRequest.objects.filter(requester=self.user1, target=self.user2, status=ChatRequest.STATUS_REQUESTED).exists())

    def test_accept_request_creates_thread(self):
        req = ChatRequest.objects.create(requester=self.user2, target=self.user1, status=ChatRequest.STATUS_REQUESTED)
        response = self.client.post(reverse('chat_interno:request-accept', args=[req.id]))
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, ChatRequest.STATUS_ACCEPTED)
        a, b = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        self.assertTrue(DirectMessageThread.objects.filter(user1=a, user2=b).exists())

    def test_decline_request_does_not_create_thread(self):
        req = ChatRequest.objects.create(requester=self.user2, target=self.user1, status=ChatRequest.STATUS_REQUESTED)
        response = self.client.post(reverse('chat_interno:request-decline', args=[req.id]))
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, ChatRequest.STATUS_DECLINED)
        self.assertFalse(DirectMessageThread.objects.exists())

    def test_requests_list_shows_incoming_and_outgoing(self):
        ChatRequest.objects.create(requester=self.user1, target=self.user2, status=ChatRequest.STATUS_REQUESTED)
        ChatRequest.objects.create(requester=self.user2, target=self.user1, status=ChatRequest.STATUS_REQUESTED)
        response = self.client.get(reverse('chat_interno:requests-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recibidas')
        self.assertContains(response, 'Enviadas')

    def test_private_start_requires_accepted_request(self):
        response = self.client.get(reverse('chat_interno:private-start', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ChatRequest.objects.filter(requester=self.user1, target=self.user2, status=ChatRequest.STATUS_REQUESTED).exists())
        self.assertFalse(DirectMessageThread.objects.exists())

    def test_private_start_with_accepted_request_creates_thread(self):
        ChatRequest.objects.create(requester=self.user1, target=self.user2, status=ChatRequest.STATUS_ACCEPTED)
        response = self.client.get(reverse('chat_interno:private-start', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        a, b = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        self.assertTrue(DirectMessageThread.objects.filter(user1=a, user2=b).exists())

    def test_blocking_prevents_sending_request(self):
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.post(reverse('chat_interno:request-send', args=[self.user2.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ChatRequest.objects.filter(requester=self.user1, target=self.user2).exists())

    def test_blocking_prevents_accepting_request(self):
        req = ChatRequest.objects.create(requester=self.user2, target=self.user1, status=ChatRequest.STATUS_REQUESTED)
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.post(reverse('chat_interno:request-accept', args=[req.id]))
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, ChatRequest.STATUS_REQUESTED)
        self.assertFalse(DirectMessageThread.objects.exists())


class ChatHomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='homeuser', password='pass')
        self.client.login(username='homeuser', password='pass')

    def test_chat_home_accessible(self):
        response = self.client.get(reverse('chat_interno:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Centro de chats')

    def test_chat_home_shows_pending_counts(self):
        other = User.objects.create_user(username='other', password='pass')
        ChatRequest.objects.create(requester=other, target=self.user, status=ChatRequest.STATUS_REQUESTED)
        ChatRequest.objects.create(requester=self.user, target=other, status=ChatRequest.STATUS_REQUESTED)
        response = self.client.get(reverse('chat_interno:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('pending_incoming', response.context)
        self.assertIn('pending_outgoing', response.context)
        self.assertEqual(response.context['pending_incoming'], 1)
        self.assertEqual(response.context['pending_outgoing'], 1)


class BlockedUserProfileAccessTests(TestCase):
    """Verifica que los perfiles y productos de usuarios bloqueados siguen siendo accesibles."""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='buyer', password='pass')
        self.user2 = User.objects.create_user(username='seller', password='pass')
        self.client.login(username='buyer', password='pass')

    def test_can_view_blocked_user_profile(self):
        """Usuario bloqueado: su perfil DEBE ser accesible."""
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.get(reverse('perfil:user_profile_view', args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user2.username)

    def test_blocked_user_profile_shows_products(self):
        """Usuario bloqueado: sus productos DEBEN ser visibles."""
        from mercado.models import Product
        product = Product.objects.create(
            seller=self.user2,
            title='Producto de prueba',
            description='Descripción del producto',
            price=100,
            stock=10,
            active=True
        )
        BlockedUser.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.get(reverse('perfil:user_profile_view', args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Producto de prueba')
        self.assertIn('user_products', response.context)
        self.assertEqual(response.context['user_products'].count(), 1)
