import math
import pygame

WIDTH, HEIGHT = 800, 600
HIVE = pygame.Vector2(400, 535)
SAFE_RADIUS = 65


def forward(angle):
    return pygame.Vector2(math.cos(angle), math.sin(angle))


def limit_speed(velocity, maximum):
    if velocity.length_squared() > maximum * maximum:
        velocity.scale_to_length(maximum)


def keep_inside(obj):
    for axis, low, high in (
        ("x", obj.radius, WIDTH - obj.radius),
        ("y", 60 + obj.radius, HEIGHT - obj.radius)
    ):
        value = getattr(obj.position, axis)

        if value < low or value > high:
            setattr(obj.position, axis, max(low, min(high, value)))
            setattr(obj.velocity, axis, 0)


class Bee:
    def __init__(self):
        self.position = HIVE.copy()
        self.velocity = pygame.Vector2()
        self.acceleration = pygame.Vector2()
        self.radius = 14
        self.health = 3
        self.carried = 0
        self.cooldown = 0

    def update(self, dt, keys):
        direction = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP])
        )

        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.acceleration = direction * 750
        self.velocity += self.acceleration * dt
        self.velocity *= 0.90 ** (dt * 60)

        limit_speed(self.velocity, 210)

        self.position += self.velocity * dt
        keep_inside(self)

        self.cooldown = max(0, self.cooldown - dt)

    def draw(self, screen):
        if self.cooldown > 0 and int(self.cooldown * 12) % 2:
            return

        pygame.draw.circle(
            screen, "yellow", self.position, self.radius
        )
        pygame.draw.circle(
            screen, "black", self.position, self.radius, 2
        )


class Flower:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.radius = 16
        self.timer = 0

    def update(self, dt):
        self.timer = max(0, self.timer - dt)

    def draw(self, screen):
        pygame.draw.circle(
            screen, "#ed8dac", self.position, self.radius
        )

        color = "#f8d465" if self.timer == 0 else "#818c80"
        pygame.draw.circle(screen, color, self.position, 6)


class Wasp:
    def __init__(self, route):
        self.route = [
            pygame.Vector2(point) for point in route
        ]

        self.position = self.route[0].copy()
        self.index = 1
        self.velocity = pygame.Vector2()
        self.acceleration = pygame.Vector2()

        direction = self.route[1] - self.position
        self.angle = math.atan2(direction.y, direction.x)

        self.radius = 14
        self.state = "PATROL"
        self.last_seen = self.position.copy()
        self.lost_time = 0

    def sees(self, bee):
        offset = bee.position - self.position
        distance = offset.length()

        return (
            distance > 0
            and distance < 180
            and forward(self.angle).dot(offset.normalize()) > 0.7
            and bee.position.distance_to(HIVE) > SAFE_RADIUS
        )

    def update(self, dt, bee):
        if bee.position.distance_to(HIVE) <= SAFE_RADIUS:
            self.state = "PATROL"
            self.lost_time = 0

        elif self.sees(bee):
            self.state = "CHASE"
            self.last_seen = bee.position.copy()
            self.lost_time = 0

        elif self.state == "CHASE":
            self.lost_time += dt

            if self.lost_time >= 2:
                self.state = "PATROL"

        if self.state == "PATROL":
            if self.position.distance_to(self.route[self.index]) < 16:
                self.index = (self.index + 1) % len(self.route)

            target = self.route[self.index]
            speed = 65

        else:
            target = self.last_seen
            speed = 95

        offset = target - self.position

        if offset.length_squared() > 0:
            desired = offset.normalize() * min(
                speed, offset.length() * 3
            )
        else:
            desired = pygame.Vector2()

        self.acceleration = (desired - self.velocity) * 3
        self.velocity += self.acceleration * dt

        limit_speed(self.velocity, 95)

        self.position += self.velocity * dt
        keep_inside(self)

        away = self.position - HIVE

        if away.length() < SAFE_RADIUS + self.radius:
            if away.length_squared() > 0:
                normal = away.normalize()
            else:
                normal = pygame.Vector2(0, -1)

            self.position = HIVE + normal * (
                SAFE_RADIUS + self.radius
            )

            inward_speed = self.velocity.dot(normal)

            if inward_speed < 0:
                self.velocity -= normal * inward_speed

        if self.velocity.length_squared() > 1:
            self.angle = math.atan2(
                self.velocity.y, self.velocity.x
            )

    def draw(self, screen, show_vision):
        if show_vision:
            layer = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )

            half_angle = math.acos(0.7)
            points = [self.position]

            for i in range(19):
                angle = (
                    self.angle
                    - half_angle
                    + i * half_angle / 9
                )

                points.append(
                    self.position + forward(angle) * 180
                )

            pygame.draw.polygon(
                layer, (255, 213, 96, 35), points
            )
            screen.blit(layer, (0, 0))

        color = "red" if self.state == "CHASE" else "orange"

        pygame.draw.circle(
            screen, color, self.position, self.radius
        )
        pygame.draw.circle(
            screen, "black", self.position, self.radius, 2
        )


class Game:
    def __init__(self):
        self.reset()
        self.show_vision = False

    def reset(self):
        self.bee = Bee()

        self.flowers = [
            Flower(position)
            for position in [
                (110, 160),
                (360, 125),
                (680, 170),
                (160, 360),
                (420, 340),
                (660, 390)
            ]
        ]

        self.wasps = [
            Wasp([(70, 110), (280, 230), (90, 430)]),
            Wasp([(490, 110), (740, 270), (520, 310)]),
            Wasp([(280, 410), (620, 450), (410, 240)])
        ]

        self.delivered = 0
        self.time_left = 90
        self.state = "PLAYING"

    def update(self, dt, keys):
        if self.state != "PLAYING":
            return

        self.bee.update(dt, keys)

        for flower in self.flowers:
            flower.update(dt)

            distance = self.bee.position.distance_to(
                flower.position
            )

            if (
                flower.timer == 0
                and self.bee.carried < 3
                and distance < self.bee.radius + flower.radius
            ):
                self.bee.carried += 1
                flower.timer = 5

        if self.bee.position.distance_to(HIVE) < 35:
            self.delivered += self.bee.carried
            self.bee.carried = 0

        for wasp in self.wasps:
            wasp.update(dt, self.bee)

            distance = self.bee.position.distance_to(
                wasp.position
            )

            if (
                self.bee.cooldown == 0
                and distance < self.bee.radius + wasp.radius
            ):
                self.bee.health -= 1
                self.bee.carried = 0
                self.bee.cooldown = 1

        self.time_left = max(0, self.time_left - dt)

        if self.bee.health <= 0:
            self.state = "LOST"

        elif self.delivered >= 12:
            self.state = "WON"

        elif self.time_left <= 0:
            self.state = "LOST"

    def draw(self, screen, font, title_font):
        screen.fill("#7baf75")

        for x in range(20, WIDTH, 70):
            for y in range(90, HEIGHT, 65):
                pygame.draw.line(
                    screen,
                    "#6b9f66",
                    (x, y),
                    (x + 3, y - 7),
                    2
                )

        pygame.draw.circle(
            screen, "#b8cf91", HIVE, SAFE_RADIUS
        )

        pygame.draw.rect(
            screen,
            "#8e603f",
            (370, 513, 60, 44),
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            "#5d4031",
            (392, 534, 16, 23),
            border_radius=5
        )

        text(
            screen, font, "HIVE", (400, 575), centered=True
        )

        for flower in self.flowers:
            flower.draw(screen)

        for wasp in self.wasps:
            wasp.draw(screen, self.show_vision)

        self.bee.draw(screen)

        pygame.draw.rect(
            screen, "#233b32", (0, 0, WIDTH, 60)
        )

        text(
            screen,
            font,
            f"Score: {self.delivered * 10}   Health: {self.bee.health}",
            (16, 12),
            color="white"
        )

        text(
            screen,
            font,
            f"Carry: {self.bee.carried}/3   Delivered: {self.delivered}/12",
            (280, 12),
            color="white"
        )

        text(
            screen,
            font,
            f"Time: {math.ceil(self.time_left)}",
            (690, 12),
            color="white"
        )

        if self.state != "PLAYING":
            shade = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            shade.fill((13, 30, 24, 220))
            screen.blit(shade, (0, 0))

            title = (
                "You Won!" if self.state == "WON" else "Game Over"
            )

            lines = [
                f"Final score: {self.delivered * 10}",
                f"Pollen delivered: {self.delivered}/12",
                "Press R to restart    Esc to quit"
            ]

            text(
                screen,
                title_font,
                title,
                (400, 170),
                "#f7ce62",
                True
            )

            for i, line in enumerate(lines):
                text(
                    screen,
                    font,
                    line,
                    (400, 250 + i * 38),
                    "white",
                    True
                )


def text(
    screen,
    font,
    message,
    position,
    color="#233b32",
    centered=False
):
    surface = font.render(message, True, color)

    if centered:
        screen.blit(
            surface, surface.get_rect(center=position)
        )
    else:
        screen.blit(surface, position)


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pollen Run")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 23)
    title_font = pygame.font.Font(None, 64)

    game = Game()
    running = True

    while running:
        dt = min(clock.tick(60) / 1000, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif (
                    event.key == pygame.K_r
                    and game.state in ("WON", "LOST")
                ):
                    game.reset()

                elif event.key == pygame.K_v:
                    game.show_vision = not game.show_vision

        game.update(dt, pygame.key.get_pressed())
        game.draw(screen, font, title_font)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()