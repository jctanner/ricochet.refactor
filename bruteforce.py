#!/usr/bin/env python

import math
import random
import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
from pprint import pprint


URL = 'http://www.robotreboot.com/classic'

RGB_MAP = {
    (85,85,255): 'blue',
    (252,255,31): 'yellow',
    (0,142,0): 'green'
}


class NoSpotsLeft(Exception):
    pass



def get_distance(a, b):
    # https://www.w3resource.com/python-exercises/python-basic-exercise-40.php
    #p1 = [4, 0]
    #p2 = [6, 6]
    #math.sqrt( ((p1[0]-p2[0])**2)+((p1[1]-p2[1])**2) )
    dist = math.sqrt(
        ((a[0] - b[0]) ** 2)
        +
        ((a[1] - b[1]) ** 2)
    )
    return dist


def distance_to_blocks(distance):
    block_width = 589 / 16
    #blocks = math.ceil(distance / 60)
    #blocks = round(distance / 60)
    #blocks = round(distance / block_width)
    blocks = math.ceil(distance / block_width)
    return blocks


def is_opposite_direction(a,b):

    if sorted([a, b]) == ['left', 'right']:
        return True
    if sorted([a, b]) == ['down', 'up']:
        return True

    return False


def style_to_color(em):
    style = em.get_attribute('style')

    if 'darkorange' in style:
        return  'yellow'

    if 'rgb' in style:
        rgb = style.split(':')[-1].replace('rgb', '').replace(';', '')
        try:
            rgb = eval(rgb)
        except Exception as e:
            print(e)
            import epdb; epdb.st()
        color = RGB_MAP[rgb]
    else:
        color = style.split(':')[-1].replace(';','').strip()
    
    return color


def get_style_map(em):
    styletxt = em.get_attribute('style')
    styles = [x.strip() for x in styletxt.split(';') if x.strip()]
    sdict = {}
    for style in styles:
        sparts = [x.strip() for x in style.split(':')]
        sdict[sparts[0]] = sparts[1]
    return sdict


def get_style_key(em, key):
    sdict = get_style_map(em)
    return sdict[key]


class Robot:

    def __init__(self, driver, container):
        self.container = container
        self.driver = driver
    
    def click(self):
        self.container.click()

    @property
    def color(self):
        robot = self.container.find_element_by_class_name('robot')
        return style_to_color(robot)

    @property
    def top(self):
        pixel = get_style_key(self.container, 'top')
        val = int(pixel.replace('px', ''))
        return val

    @property
    def left(self):
        pixel = get_style_key(self.container, 'left')
        val = int(pixel.replace('px', ''))
        return val
    
    @property
    def coord(self):
        return (self.top, self.left)

    @property
    def arrows(self):
        arrows = {}
        for adiv in self.container.find_elements_by_class_name('arrow'):
            arrow = Arrow(self.driver, adiv, self)
            arrows[arrow.direction] = arrow
            # print(f'ARROW: {arrow.direction}')
        return arrows


class Goal(Robot):
    
    @property
    def color(self):
        i = self.container.find_element_by_tag_name('i')
        return style_to_color(i)


class Arrow(Robot):

    def __init__(self, driver, container, parent):
        self.driver = driver
        self.container = container
        self.parent = parent

    @property
    def direction(self):
        classes = self.container.get_attribute('class')
        direction = classes.split()[-1].replace('arrow-', '')
        return direction   

    @property
    def distance(self):

        sdict = get_style_map(self.container)

        # if blocked, the line is not displayed ...
        if 'display' in sdict and sdict['display'] == 'none':
            return 0

        # invalid direction?
        if 'width' not in sdict or 'height' not in sdict:
            return 0

        vals = [
            abs(int(sdict['width'].replace('px', ''))),
            abs(int(sdict['height'].replace('px', '')))
        ]

        distance = max(vals)
        blocks = distance_to_blocks(distance)
        print(f'{self.parent.color} {self.container.id} {self.direction} = {distance}d ... t{self.top},l{self.left} ... {blocks} blocks')

        return max(vals)


class RobotRebaser:

    def __init__(self):
        self.driver = webdriver.Chrome(ChromeDriverManager().install())
        self._width = None
        self._height = None
        self._robot_origins = None

    def __del__(self):
        self.driver.close()
    
    @property
    def redo_button(self):
        return self.driver.find_element_by_class_name('redo')
    
    @property
    def soup(self):
        return BeautifulSoup(self.driver.page_source, 'html.parser')
    
    @property
    def robots(self):
        robots = {}

        robot_containers = self.driver.find_elements_by_class_name('robot-container')
        for rc in robot_containers:
            robot = Robot(self.driver, rc) 
            robots[robot.color] = robot      

        return robots
    
    @property
    def goal(self):
        goal_container = self.driver.find_element_by_class_name('goal-container')
        goal = Goal(self.driver, goal_container)
        return goal
    
    def reload(self):
        self.driver.get(URL)
        time.sleep(2)
        canvas = self.driver.find_element_by_tag_name('canvas')
        canvas.screenshot('/tmp/canvas.png')
        self._width = int(canvas.get_attribute('width'))
        self._height = int(canvas.get_attribute('height'))

        robots = self.robots
        goal = self.goal

    def is_blocked(self, robot, direction, coord):
        # does this direction hit a wall?
        if robot.arrows['up'].distance <= 0:
            return True
        
        import epdb; epdb.st()



    def force_one_color(self):

        color = self.goal.color
        this_coord = self.robots[color].coord
        last_direction = None

        visited = set()
        visits_by_destination = {}


        def random_path():
            # map out the distances of all possible directions
            distances = [(
                x.distance,
                distance_to_blocks(x.distance),
                x.coord,
                x.direction
            ) for x in self.robots[color].arrows.values()]
            pprint(distances)

            for x in distances:
                if x[2] == self.goal.coord:
                    return x

            # don't go backwards
            if last_direction:
                distances = [x for x in distances if not is_opposite_direction(last_direction, x[-1])]
            
            # avoid collisions
            distances = [x for x in distances if x[1] > 0]
            
            # don't go back to previously visited spots
            dcoords = [x[2] for x in distances]
            dcoords_unvisited = [x for x in dcoords if x not in visits_by_destination]
            if not dcoords_unvisited:
                print('We ran out of places to go and are circling! (1)')
                raise NoSpotsLeft
           
            maxd = random.choice([x[0] for x in distances])

            togo = [x for x in distances if x[0] == maxd]
            return togo 

        def longest_path():
            # map out the distances of all possible directions
            distances = [(
                x.distance,
                distance_to_blocks(x.distance),
                x.coord,
                x.direction
            ) for x in self.robots[color].arrows.values()]
            pprint(distances)

            for x in distances:
                if x[2] == self.goal.coord:
                    return x

            # don't go backwards
            if last_direction:
                distances = [x for x in distances if not is_opposite_direction(last_direction, x[-1])]
            
            # avoid collisions
            distances = [x for x in distances if x[1] > 0]
            
            # don't go back to previously visited spots
            dcoords = [x[2] for x in distances]
            dcoords_unvisited = [x for x in dcoords if x not in visits_by_destination]
            if not dcoords_unvisited:
                print('We ran out of places to go and are circling! (1)')
                raise NoSpotsLeft
           
            maxd = max([x[0] for x in distances])
            #maxd = min([x[0] for x in distances])

            togo = [x for x in distances if x[0] == maxd]
            return togo            

        def nearest_to_goal():
            # map out the distance to the goal for all possible directions
            distances = [(
                get_distance(x.coord, self.goal.coord),
                x.distance,
                x.coord,
                x.direction
            ) for x in self.robots[color].arrows.values()]
            pprint(distances)            

            for x in distances:
                if x[2] == self.goal.coord:
                    return x

            # don't go backwards
            if last_direction:
                distances = [x for x in distances if not is_opposite_direction(last_direction, x[-1])]
            
            # avoid collisions
            distances = [x for x in distances if x[1] > 0]
            
            # don't go back to previously visited spots
            dcoords = [x[2] for x in distances]
            dcoords_unvisited = [x for x in dcoords if x not in visits_by_destination]
            if not dcoords_unvisited:
                print('We ran out of places to go and are circling! (2)')
                raise NoSpotsLeft
           
            #maxd = max([x[0] for x in distances])
            maxd = min([x[0] for x in distances])

            togo = [x for x in distances if x[0] == maxd]
            return togo

        strategies = ['nearest_to_goal()', 'longest_path()', 'random_path()']
        strategy = random.choice(strategies)

        while True:

            print(f'VISITED COUNT: {len(list(visited))}')

            if len(list(visited)) > 20:
                strategy = random.choice(strategies)
                self.redo_button.click()
                visited = set()
                visits_by_destination = {}
                #import epdb; epdb.st()

            self.robots[color].click()
            print(f'current location: {self.robots[color].coord}')

            #togo = nearest_to_goal()
            try:
                togo = eval(strategy)
            except NoSpotsLeft as e:
                break

                '''
                #strategy = 'longest_path()'
                strategy = random.choice(strategies)
                visited = set()
                visits_by_destination = {}

                try:
                    togo = eval(strategy)
                except NoSpotsLeft as e:
                    self.redo_button.click()
                    break
                '''

            desired_direction = togo[0][-1]
            desired_destination = togo[0][-2]

            print(f'attempting to go {desired_direction}')
            #import epdb; epdb.st()
            try:
                self.robots[color].arrows[desired_direction].click()
                last_direction = desired_direction
            except Exception as e:
                print(e)
                import epdb; epdb.st()
            
            if self.goal.color != color:
                print('Goal color changed. Guess we found the spot?')
                break

            if self.robots[color].coord == self.goal.coord:
                print('Seems that we got to the goal?')
                break
        
            if self.robots[color].coord in visited:
                print('We are stuck!')
                self.redo_button.click()
                break

            visited.add(self.robots[color].coord)
            visits_by_destination[desired_destination] = self.robots[color].coord
            #import epdb; epdb.st()



def main():
    rr = RobotRebaser()
    rr.reload()

    while True:
        rr.force_one_color()
        rr.redo_button.click()
        #import epdb; epdb.st()
        time.sleep(3)
        print('####################################################')
        print('STARTING NEW CYCLE ...')
        print('####################################################')


if __name__ == "__main__":
    main()