import heapq
import random
import threading
import time
import tkinter as tk


class NetworkSimulator:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=1000, height=800, bg="white")
        self.canvas.pack()
        self.nodes = {}
        self.links = {}
        self.adjacency_list = {}
        self.running = True
        self.packet_loss_probability = 0.1  # Вероятность потери пакета

        # Создаем узлы
        self.create_node("A", 100, 300)
        self.create_node("B", 300, 100)
        self.create_node("C", 500, 300)
        self.create_node("D", 300, 500)
        self.create_node("E", 700, 300)
        self.create_node("F", 500, 500)
        self.create_node("G", 700, 500)

        # Создаем соединения
        self.create_link("A", "B", 1)
        self.create_link("B", "C", 1)
        self.create_link("C", "D", 1)
        self.create_link("D", "A", 1)
        self.create_link("C", "E", 1)
        self.create_link("E", "F", 1)
        self.create_link("F", "G", 1)
        self.create_link("D", "F", 1)

        # Инициализируем распределенное хранилище
        self.initialize_data_storage()

        # Добавляем кнопки управления
        self.create_controls()

        # Обновляем таблицы маршрутизации
        self.update_routing_tables()

    def create_node(self, name, x, y):
        """Создает узел в указанной точке."""
        node = {
            "name": name,
            "x": x,
            "y": y,
            "id": self.canvas.create_oval(x - 20, y - 20, x + 20, y + 20, fill="lightblue"),
            "label": self.canvas.create_text(x, y, text=name),
            "routing_table": {},
            "data": {},  # Локальное хранилище данных
        }
        self.nodes[name] = node
        self.adjacency_list[name] = {}

    def create_link(self, node1, node2, cost):
        """Создает соединение между двумя узлами с указанной стоимостью."""
        x1, y1 = self.nodes[node1]["x"], self.nodes[node1]["y"]
        x2, y2 = self.nodes[node2]["x"], self.nodes[node2]["y"]
        link = self.canvas.create_line(x1, y1, x2, y2, width=2)
        self.canvas.tag_lower(link)
        self.links[(node1, node2)] = {"line": link, "cost": cost, "active": True}
        self.links[(node2, node1)] = {"line": link, "cost": cost, "active": True}
        self.adjacency_list[node1][node2] = cost
        self.adjacency_list[node2][node1] = cost

    def toggle_link(self, node1, node2):
        """Включает или отключает соединение между двумя узлами."""
        if (node1, node2) in self.links:
            link = self.links[(node1, node2)]
            if link["active"]:
                self.canvas.itemconfig(link["line"], dash=(5, 5), fill="gray")
                link["active"] = False
                self.links[(node2, node1)]["active"] = False
                del self.adjacency_list[node1][node2]
                del self.adjacency_list[node2][node1]
                print(f"Соединение между {node1} и {node2} разорвано.")
            else:
                self.canvas.itemconfig(link["line"], dash=(), fill="black")
                link["active"] = True
                self.links[(node2, node1)]["active"] = True
                self.adjacency_list[node1][node2] = link["cost"]
                self.adjacency_list[node2][node1] = link["cost"]
                print(f"Соединение между {node1} и {node2} восстановлено.")

            self.update_routing_tables()

    def initialize_data_storage(self):
        """Распределяет данные между узлами."""
        data_chunks = {
            "file1": ["chunk1", "chunk2", "chunk3"],
            "file2": ["chunk1", "chunk2"],
        }
        nodes = list(self.nodes.keys())

        for file, chunks in data_chunks.items():
            for i, chunk in enumerate(chunks):
                node = nodes[i % len(nodes)]
                self.nodes[node]["data"][file] = self.nodes[node]["data"].get(file, []) + [chunk]

        print("Распределение данных по узлам:")
        for node, data in self.nodes.items():
            print(f"Узел {node}: {data['data']}")

    def dijkstra(self, start_node):
        """Выполняет алгоритм Дейкстры для поиска кратчайших путей."""
        distances = {node: float('inf') for node in self.nodes}
        distances[start_node] = 0
        priority_queue = [(0, start_node)]
        previous_nodes = {}

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_distance > distances[current_node]:
                continue

            for neighbor, cost in self.adjacency_list[current_node].items():
                distance = current_distance + cost
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        return distances, previous_nodes

    def update_routing_tables(self):
        """Обновляет таблицы маршрутизации всех узлов."""
        for node in self.nodes:
            distances, _ = self.dijkstra(node)
            self.nodes[node]["routing_table"] = distances

    def request_data(self, src, dst, file):
        """Запрашивает данные у других узлов и собирает их по кускам."""
        threading.Thread(target=self._request_data, args=(src, dst, file)).start()

    def _request_data(self, src, dst, file):
        """Логика передачи данных в отдельном потоке."""
        print(f"{src} запрашивает файл {file} у сети.")
        collected_chunks = []
        threads = []

        for node, data in self.nodes.items():
            if file in data["data"]:
                for chunk in data["data"][file]:
                    thread = threading.Thread(target=self.send_packet, args=(node, src, chunk, collected_chunks))
                    threads.append(thread)
                    thread.start()

        for thread in threads:
            thread.join()

        if len(collected_chunks) == len(self.nodes[dst]["data"].get(file, [])):
            print(f"Файл {file} успешно собран на {src}: {collected_chunks}")
        else:
            print(f"Файл {file} собран частично на {src}: {collected_chunks}")

    def send_packet(self, src, dst, chunk, result):
        """Передача данных между узлами."""
        route = self.get_route(src, dst)
        if not route:
            print(f"Нет маршрута из {src} в {dst}")
            return False

        for i in range(len(route) - 1):
            current, next_hop = route[i], route[i + 1]
            if not self.simulate_packet(current, next_hop, chunk):
                return False
        result.append(chunk)
        return True

    def simulate_packet(self, src, dst, chunk):
        """Имитирует передачу данных между двумя узлами."""
        src_node = self.nodes[src]
        dst_node = self.nodes[dst]
        packet = self.canvas.create_oval(src_node["x"] - 5, src_node["y"] - 5,
                                         src_node["x"] + 5, src_node["y"] + 5, fill="orange")
        steps = 20
        dx = (dst_node["x"] - src_node["x"]) / steps
        dy = (dst_node["y"] - src_node["y"]) / steps

        for _ in range(steps):
            self.canvas.move(packet, dx, dy)
            self.canvas.update()
            time.sleep(0.05)

        if random.random() < self.packet_loss_probability:
            self.canvas.itemconfig(packet, fill="gray")
            print(f"Пакет с данными {chunk} потерян между {src} и {dst}")
            self.canvas.delete(packet)
            return False
        else:
            self.canvas.delete(packet)
            return True

    def get_route(self, src, dst):
        """Находит маршрут из таблицы маршрутизации."""
        distances, previous_nodes = self.dijkstra(src)
        if distances[dst] == float('inf'):
            return None
        route = []
        while dst:
            route.append(dst)
            dst = previous_nodes.get(dst)
        return route[::-1]

    def create_controls(self):
        """Создает кнопки управления."""
        frame = tk.Frame(self.root)
        frame.pack()

        request_button = tk.Button(frame, text="Запросить файл", command=self.handle_request)
        request_button.pack(side=tk.LEFT)

        toggle_button = tk.Button(frame, text="Разрыв соединения", command=self.handle_toggle)
        toggle_button.pack(side=tk.LEFT)

    def handle_request(self):
        """Обработчик запроса файла."""
        self.request_data("A", "B", "file1")

    def handle_toggle(self):
        """Обработчик разрыва соединений."""
        self.toggle_link("B", "C")
        self.toggle_link("A", "D")


root = tk.Tk()
simulator = NetworkSimulator(root)
root.mainloop()
