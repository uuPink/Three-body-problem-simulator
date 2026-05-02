from time import time
from scipy import integrate
import numpy as np
from math import sqrt

#----------calc.py
#Contains all calculation and animation modules (except for some which are in main.py)
#One thing that you should know is that positions is both called steps and positions it depends on where you read it. This code is so chopped.

class Body:
    def __init__(self, mass, startxyz: tuple, startvelxyz: tuple, radius, color, label):
        self.startpos = (startxyz[0], startxyz[1], startxyz[2])
        self.startvel = startvelxyz

        self.mass = mass
        self.pos = self.startpos
        self.vel = self.startvel
        self.radius = radius

        self.color = color
        self.label = label
    
    def __str__(self):
        return (f"""Startposition:  {self.startpos}       Startvelocity:    {self.startvel}       Mass:     {self.mass}            Radius:      {self.radius}              Color:   {self.color}               Label:   {self.label}""")

class BodyManager:
    def __init__(self, bodies):
        self.bodies = bodies
        
        #Calculated trajectories as is. [[[x1, x2, x2],[y1, y2, y3],[z1, z2, z3]],[[x1, x2, x3],[y1, y2, y3],[z1, z2, z3]]]
        #z always included just not significant if 2d render. 
        self.trajectories = []

        #List of frames, which are lists of the plotted lines and scatters for that frame. 
        #[[line1, scatter1, line2, scatter2, line3, scatter3], [line1, scatter1, line2, scatter2, line3, scatter3]]
        self.frames = []

        #List of distance between bodies for each frame. [[frame index, distance 1-2, distance 1-3, distance 2-3]]
        self.dists = []
    
    def three_body_equations(self, t, state, m1, m2, m3):
        #Includes z, which when 0 doesn't change x or y. 
        G = 6.67430e-11
        x1, y1, z1, x2, y2, z2, x3, y3, z3, vx1, vy1, vz1, vx2, vy2, vz2, vx3, vy3, vz3 = state

        pos1 = np.array([x1, y1, z1])
        pos2 = np.array([x2, y2, z2])
        pos3 = np.array([x3, y3, z3])

        pos12 = pos1-pos2
        pos13 = pos1-pos3
        pos23 = pos2-pos3
        dist12 = np.linalg.norm(pos12)
        dist13 = np.linalg.norm(pos13)
        dist23 = np.linalg.norm(pos23)

        a1 = -G * m2 * pos12 / dist12**3 - G * m3 * pos13 / dist13**3
        a2 = -G * m1 * (-pos12) / dist12**3 - G * m3 * pos23 / dist23**3
        a3 = -G * m1 * (-pos13) / dist13**3 - G * m2 * (-pos23) / dist23**3

        return (vx1, vy1, vz1, vx2, vy2, vz2, vx3, vy3, vz3, a1[0], a1[1], a1[2], a2[0], a2[1], a2[2], a3[0], a3[1], a3[2])

    def calculate_positions(self, t_start = 0, t_end = 31536000*1.5, positions = 2500):
        """
        Integrates the differential equation for given self.bodies with positions number of steps in the timespan 0 -> t_end.
        \nReturns solve time
        """

        t = time()
        #t_end: Simulation time; positions: number of solutions (positions) calculated. 
        # More positions => more accurate result (remember to update slicesizes as well). 
        # The longer the simulation the more positions and frames are needed to display in a good way
        t_eval = np.linspace(t_start, t_end, positions)
        #x1, y1, z1, x2, y2, z2, x3, y3, z3, vx1, vy1, vz1, vx2, vy2, vz2, vx3, vy3, vz3
        state0 = (self.bodies[0].pos[0], self.bodies[0].pos[1], self.bodies[0].pos[2], self.bodies[1].pos[0], self.bodies[1].pos[1], self.bodies[1].pos[2], self.bodies[2].pos[0], self.bodies[2].pos[1], self.bodies[2].pos[2], self.bodies[0].vel[0], self.bodies[0].vel[1], self.bodies[0].vel[2], self.bodies[1].vel[0], self.bodies[1].vel[1], self.bodies[1].vel[2], self.bodies[2].vel[0], self.bodies[2].vel[1], self.bodies[2].vel[2])
        
        #RK45 is the default method, DOP853 is RK but more precise. 
        solution = integrate.solve_ivp(self.three_body_equations, (0, t_end), state0, method="DOP853", args=(self.bodies[0].mass, self.bodies[1].mass, self.bodies[2].mass), t_eval=t_eval, rtol=1e-9, atol=1e-12)

        solve_time = time()-t
        print("Solving time:", solve_time)

        #Trajectory paths
        body1_path = (solution.y[0], solution.y[1], solution.y[2])
        body2_path = (solution.y[3], solution.y[4], solution.y[5])
        body3_path = (solution.y[6], solution.y[7], solution.y[8])

        #Velocities
        #Now 3d is officially obsolete as I stop taking the data of 3d velocities from the solution.
        vel1 = solution.y[9], solution.y[10]
        vel2 = solution.y[12], solution.y[13]
        vel3 = solution.y[15], solution.y[16]

        self.trajectories = [body1_path, body2_path, body3_path]
        self.velocities = [vel1, vel2, vel3]

        return solve_time
    
    def animate_trajectories(self, slicesize = 40, framedelay = 30, MODE = 2, DARK = False, SHOWDISTS = False):
        if len(self.trajectories) != 3: print("No calculated trajectories, returning..."); return
        #-------Setup of matplotlib
        d = time()
        import matplotlib.pyplot as plt
        from matplotlib.animation import ArtistAnimation
        print("matplotlib import time:", time()-d)

        if DARK: plt.style.use('dark_background')
        
        fig = plt.figure(num=0, figsize=(8,8))

        if MODE == 3: ax = fig.add_subplot(projection="3d")

        plt.xlabel('x [m]')
        plt.ylabel('y [m]')
        plt.title('Three-Body Problem')
        #-------End of setup
        t = time()
        self.frames = []

        #from position 0 take every slicesize'th position, cutting from 2000 to 2000/slicesize frames per trajectory. Lower = more frames from result showed. This is to save time in drawing.
        trajectories = []
        for trajectory in self.trajectories:
            cut_trajectory = []
            for i in range(0, MODE):
                #Grab the last position if it's not included in the slice
                if (trajectory[i][::slicesize][-1] != trajectory[i][-1]): cut_trajectory.append(trajectory[i][::slicesize]); cut_trajectory[-1] = np.append(cut_trajectory[-1], trajectory[i][-1])
                #Edge case; all positions are the same (e.g. 0.0) and won't show up as missing the last position in the cut trajectory. We append this repeated value to the end.
                elif (trajectory[i][-1] == trajectory[i][-2]): cut_trajectory.append(trajectory[i][::slicesize]); cut_trajectory[-1] = np.append(cut_trajectory[-1], trajectory[i][-1])
                #Normal case; Everything's included in the slice and so we just add it to the cut trajectory
                else: cut_trajectory.append(trajectory[i][::slicesize])
            trajectories.append(cut_trajectory)
        
        for i in range(1, len(trajectories[0][0])+1):
            self.frames.append([])

            #2d
            if MODE == 2:
                for j in range(0, 3):
                    self.frames[i-1].append(plt.plot(trajectories[j][0][:i], trajectories[j][1][:i], c=self.bodies[j].color)[0])
                    self.frames[i-1].append(plt.scatter(trajectories[j][0][i-1], trajectories[j][1][i-1], c=self.bodies[j].color))
            #3d
            elif MODE == 3:
                for j in range(0, 3):
                    self.frames[i-1].append(ax.plot(trajectories[j][0][:i], trajectories[j][1][:i], trajectories[j][2][:i], c=self.bodies[j].color)[0])
                    self.frames[i-1].append(ax.scatter(trajectories[j][0][i-1], trajectories[j][1][i-1], trajectories[j][2][i-1], c=self.bodies[j].color))
        
        #Set labels for each scatter in the first frame which will be carried on to the next frames.
        self.frames[0][0].set_label(self.bodies[0].label)
        self.frames[0][2].set_label(self.bodies[1].label)
        self.frames[0][4].set_label(self.bodies[2].label)

        print("Animation setup-time:", time()-t)


        #-------Start animation:
        t = time()

        anim = ArtistAnimation(fig, self.getFrames(), framedelay)
        #anim.save("Test1.gif")

        #plt.legend()
        plt.grid(alpha=0.25)
        plt.axis('equal')
        plt.legend()

        self.calculate_collisions(self.trajectories, self.bodies[0].radius, self.bodies[1].radius, self.bodies[2].radius)

        if SHOWDISTS:
            fig2 = plt.figure(num=1, figsize=(5,5))

            ax2, ax3, ax4 = fig2.subplots(3, 1)
        
            
            xlist1, ylist1, xlist2, ylist2, xlist3, ylist3 = [], [], [], [], [], []
            for dist in self.dists:
                xlist1.append(dist[0])
                ylist1.append(dist[1])

                xlist2.append(dist[0])
                ylist2.append(dist[2])

                xlist3.append(dist[0])
                ylist3.append(dist[3])
        
            ax2.plot(xlist1, ylist1)
            ax2.set_title("Distance 1-2, 1-3, 2-3")
            ax3.plot(xlist2, ylist2)
            ax4.plot(xlist3, ylist3)

            ax4.set_xlabel('x [frames]')
            ax3.set_ylabel('y [m]')

        print("Plotting time:", time()-t)

        plt.show()
    
    def calculate_collisions(self, trajectories, radius):
        #Basically useless now that we know a system will die either way when "collision" occurs since the gravitational force grows to infinity. Kept in code for ol' times sake
        #Deprecated version of calculate_collisions!! DOES NOT WORK since sci-py can't integrate when the speeds are so high and the bodies move into each other which means they will never actually touch each other
        
        #Takes both 2D and 3D as input but only works for 2D (I think)
        t = time()
        found = False
        self.dists = []

        if len(trajectories) == 0: print("No trajectories calculated, returning..."); return

        steps = []

        for i in range(0, len(trajectories[0][0])):

            pos1 = np.array([trajectories[0][0][i], trajectories[0][1][i], trajectories[0][2][i]])
            pos2 = np.array([trajectories[1][0][i], trajectories[1][1][i], trajectories[1][2][i]])
            pos3 = np.array([trajectories[2][0][i], trajectories[2][1][i], trajectories[2][2][i]])

            dist12 = np.linalg.norm(pos1-pos2)
            dist13 = np.linalg.norm(pos1-pos3)
            dist23 = np.linalg.norm(pos2-pos3)

            self.dists.append((i+1, dist12, dist13, dist23))

            if dist12 < (radius[0] + radius[1]): print("Collision found between body1 and body2 at:", pos1, pos2, f"respectively at step {i+1}"); found = True; steps.append(i+1)
            if dist13 < (radius[0] + radius[2]): print("Collision found between body1 and body3 at:", pos1, pos3, f"respectively at step {i+1}"); found = True; steps.append(i+1)
            if dist23 < (radius[1] + radius[2]): print("Collision found between body2 and body3 at:", pos2, pos3, f"respectively at step {i+1}"); found = True; steps.append(i+1)

        if not found: 
            print("No collisions found between bodies")
        
        print("Collision calculation time: ", time()-t)
        return ([steps, self.dists])
    
    def calculate_lifespan1(self, trajectories, velocities, mass, t_start, t_end, steps, save_acc = False, save_vel = False, acc_tol = 0.5, t_lifetol = 0.9, analyse=True):
        """
        First version. Accurate to a certain degree but does not scale with system so smaller systems might face problems. 

        Doesn't work with 3d.

        acc_tol for which acceleration a body must have to count as still active in the system.
        t_lifetol - t_lifetol*tmax for how close to the end of the simulation a body can turn unactive but still count as active because of uncertainty of what happens after the simulation ends.

        analyse: if False, won't calculate lifespan (useful for example when savetoexcel wants the velocities but doesn't need lifespan)
        """

        G = 6.67430e-11
        m1, m2, m3 = mass[0], mass[1], mass[2]

        ac1x, ac1y, ac2x, ac2y, ac3x, ac3y = [], [], [], [], [], []
        v1, v2, v3 = velocities[0], velocities[1], velocities[2]

        steps = int(steps)

        t = time()

        #Times at which a solution was saved
        t_list = np.linspace(t_start, t_end, steps)
        

        lifespan = 0

        ls1 = [0,0]
        ls2 = [0,0]
        ls3 = [0,0]

        #Tolerance for what kind of acceleration means a body is still integrated in the system. 
        acctol = acc_tol

        #For each step, calculate acceleration on each body and compare to the energy of the moving body.
        for step in range(0, steps):
            x1, y1, x2, y2, x3, y3 = trajectories[0][step], trajectories[1][step], trajectories[2][step], trajectories[3][step], trajectories[4][step], trajectories[5][step]

            pos1 = np.array([x1, y1])
            pos2 = np.array([x2, y2])
            pos3 = np.array([x3, y3])

            pos12 = pos1-pos2
            pos13 = pos1-pos3
            pos23 = pos2-pos3
            dist12 = np.linalg.norm(pos12)
            dist13 = np.linalg.norm(pos13)
            dist23 = np.linalg.norm(pos23)

            #Formula for acceleration on body when two gravitational forces affect a body
            #a1 for force excerted on body 1 from body 2 and 3, and so on...
            a1 = -G * m2 * pos12 / dist12**3 - G * m3 * pos13 / dist13**3
            a2 = -G * m1 * (-pos12) / dist12**3 - G * m3 * pos23 / dist23**3
            a3 = -G * m1 * (-pos13) / dist13**3 - G * m2 * (-pos23) / dist23**3

            #Adding to list for graphing purposes
            ac1x.append(a1[0])
            ac2x.append(a2[0])
            ac3x.append(a3[0])
            ac1y.append(a1[1])
            ac2y.append(a2[1])
            ac3y.append(a3[1])

            #---Calculating lifespan
            t_current = t_list[step]
            t_max = t_end-t_start
            
            if analyse:
                #Basically how this works is that we're checking if the acceleration is greater than acctol to see if a body is still in the system. ls1 can be seen as a "time of death" counter as it 
                #resets every time it's confirmed that the system is alive but as soon as it's not proved to be alive and doesn't already have a saved time of death will become the current time which then acts as the new time of death. 
                if any(abs(a1) > acctol):
                    #Acceleration going away from 0: clear list as the system is not dead yet.
                    ls1 = [0,0]
                else:
                    if ls1 == [0,0]:
                        #If acceleration around 0: add time to list as we want to keep track of the lifespan. 
                        ls1 = [t_current, step+1]
                
                if any(abs(a2) > acctol):
                    ls2 = [0,0]
                else:
                    if ls2 == [0,0]:
                        ls2 = [t_current, step+1]
                
                if any(abs(a3) > acctol):
                    ls3 = [0,0]
                else:
                    if ls3 == [0,0]:
                        ls3 = [t_current, step+1]

        if analyse:
            #Convert [0,0] to [t_max,steps] since those with [0,0] has not affected the lifespan
            if ls1 == [0,0]: ls1 = [t_max, steps]
            if ls2 == [0,0]: ls2 = [t_max, steps]
            if ls3 == [0,0]: ls3 = [t_max, steps]

            #Tolerance of how late in the simulation a system can act dead but still be considered alive since we might not be able to tell what happens after the simulation ends.
            #Basically: if time of death is later than the step at which we can't predict the future too well, assume death did not occur.
            tlifetol = t_lifetol*t_max

            if ls1[0]-t_start>tlifetol and ls2[0]-t_start>tlifetol and ls3[0]-t_start>tlifetol:
                lifespan = [t_max, steps]
            else:
                #Choose earliest time of death and set actual time of death by subtracting starting time. 
                lifespan = [min(ls1[0], ls2[0], ls3[0])-t_start,min(ls1[1], ls2[1], ls3[1])]

            print("Lifespan:", lifespan[0], "seconds at step:", lifespan[1])
        calc_time = time()-t
        print("Calculation time:", calc_time)
        
        return ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time
    
    def calculate_lifespan2(self, trajectories, velocities, mass, t_start, t_end, steps, save_acc = False, save_vel = False, acc_tol = 0.1, t_lifetol = 0.9, analyse=True):
        """
        Second version. Scales with system but does not work when bodies make both very big and very small acceleration jumps.
        Doesn't work with 3d.

        velocities unnecessary but haven't removed them from args yet.

        acc_tol - acc_tol*max difference between start acceleration and max acceleration determines how much acceleration change from start acceleration counts as a system which is alive. 
            Indirectly also determines how much acceleration is needed for a body to not be alive. Bruh I officially hate acc_tol why is this so hard. 
            The higher your acc_tol is, the harder it will be for a jump in acceleration to count as a revival of the system. 
            Therefore 0.5 is too high and 0.1 is preferred since a very large jump in the begining can make later jumps not register at all.
        t_lifetol - t_lifetol*tmax for how close to the end of the simulation a body can turn unactive but still count as active because of uncertainty of what happens after the simulation ends.

        analyse: if False, won't calculate lifespan (useful for example when savetoexcel wants the accelerations but doesn't need lifespan)
        """

        G = 6.67430e-11
        m1, m2, m3 = mass[0], mass[1], mass[2]

        ac1x, ac1y, ac2x, ac2y, ac3x, ac3y = [], [], [], [], [], []
        v1, v2, v3 = velocities[0], velocities[1], velocities[2]

        steps = int(steps)

        lifespan = 0

        t = time()

        #Times at which a solution was saved
        t_list = np.linspace(t_start, t_end, steps)

        #For each step, calculate acceleration on each body and compare to the energy of the moving body.
        for step in range(0, steps):
            x1, y1, x2, y2, x3, y3 = trajectories[0][step], trajectories[1][step], trajectories[2][step], trajectories[3][step], trajectories[4][step], trajectories[5][step]

            pos1 = np.array([x1, y1])
            pos2 = np.array([x2, y2])
            pos3 = np.array([x3, y3])

            pos12 = pos1-pos2
            pos13 = pos1-pos3
            pos23 = pos2-pos3
            dist12 = np.linalg.norm(pos12)
            dist13 = np.linalg.norm(pos13)
            dist23 = np.linalg.norm(pos23)

            #Formula for acceleration on body when two gravitational forces affect a body
            #a1 for force excerted on body 1 from body 2 and 3, and so on...
            a1 = -G * m2 * pos12 / dist12**3 - G * m3 * pos13 / dist13**3
            a2 = -G * m1 * (-pos12) / dist12**3 - G * m3 * pos23 / dist23**3
            a3 = -G * m1 * (-pos13) / dist13**3 - G * m2 * (-pos23) / dist23**3

            #Adding to list for graphing purposes
            ac1x.append(a1[0])
            ac2x.append(a2[0])
            ac3x.append(a3[0])
            ac1y.append(a1[1])
            ac2y.append(a2[1])
            ac3y.append(a3[1])


        if analyse:
            ls1 = [0,0]
            ls2 = [0,0]
            ls3 = [0,0]

            #Turning all accelerations into absolute values
            abs_acc = []
            for acc in ac1x, ac1y, ac2x, ac2y, ac3x, ac3y:
                abs_acc.append([abs(ac) for ac in acc])
            
            #Setting the tolerances for each body for what kind of acceleration means they are still integrated in the system.
            tols = []
            for acc in abs_acc:
                start = acc[0]
                maxtol = max(acc)

                #Security for if max(acc) is some wild number. If maxtol is bigger than two times the second largest maxtol then the second largest maxtol is used since the largest one is unrealistic.
                new_list = acc.copy()
                new_list.remove(maxtol)
                second_maxtol = max(new_list)
                if maxtol>2*second_maxtol:
                    maxtol = second_maxtol

                tol = acc_tol*max(maxtol-start, start-maxtol)
                tols.append(tol)
            print(tols)
            #---Calculating lifespan
            t_max = t_end-t_start
            
            starts = [acc[0] for acc in abs_acc]
            for step in range(0, steps):
                t_current = t_list[step]

                #Basically how this works is that w're checking if the difference in acceleration of a step is bigger than acc_tol*the largest difference in acceleration found in the data compared to the start.
                #If True, the body is still in the system as it still interacting with the other bodies. ls1 can be seen as a "time of death" counter as it resets every time it's confirmed that the
                #system is alive but as soon as it's not proved to be alive and doesnn't have a saed time of death will become the current time which then becomes the time of death.
                if abs_acc[0][step]-starts[0]>tols[0] or abs_acc[1][step]-starts[1]>tols[1]:
                    #Acceleration going away from 0: clear list as the system is not dead yet.
                    ls1 = [0,0]
                else:
                    if ls1 == [0,0]:
                        #If acceleration around 0: add time to list as we want to keep track of the lifespan. 
                        ls1 = [t_current, step+1]
                
                if abs_acc[2][step]-starts[2]>tols[2] or abs_acc[3][step]-starts[3]>tols[3]:
                    ls2 = [0,0]
                else:
                    if ls2 == [0,0]:
                        ls2 = [t_current, step+1]
                
                if abs_acc[4][step]-starts[4]>tols[4] or abs_acc[5][step]-starts[5]>tols[5]:
                    ls3 = [0,0]
                else:
                    if ls3 == [0,0]:
                        ls3 = [t_current, step+1]
            print(ls1, ls2, ls3)
            #Convert [0,0] to [t_max,steps] since those with [0,0] has not affected the lifespan
            if ls1 == [0,0]: ls1 = [t_max, steps]
            if ls2 == [0,0]: ls2 = [t_max, steps]
            if ls3 == [0,0]: ls3 = [t_max, steps]

            #Tolerance of how late in the simulation a system can act dead but still be considered alive since we might not be able to tell what happens after the simulation ends.
            #Basically: if time of death is later than the step at which we can't predict the future too well, assume death did not occur.
            tlifetol = t_lifetol*t_max

            if ls1[0]-t_start>tlifetol and ls2[0]-t_start>tlifetol and ls3[0]-t_start>tlifetol:
                lifespan = [t_max, steps]
            else:
                #Choose earliest time of death and set actual lifespan by subtracting starting time. 
                lifespan = [min(ls1[0], ls2[0], ls3[0])-t_start,min(ls1[1], ls2[1], ls3[1])]

            print("Lifespan:", lifespan[0], "seconds at step:", lifespan[1])
        calc_time = time()-t
        print("Calculation time:", calc_time)
        
        return ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time

    def calculate_lifespan3(self, trajectories, velocities, mass, t_start, t_end, steps, save_acc = False, save_vel = False, acc_tol = 100, t_lifetol = 0.9, analyse=True):
        """
        Third version. Works good as long as acceleration jumps are bigger than acc_tol times the start acceleration. Might work bad if acceleration-norm changes after half of the simulation.
        Yeah now it works bad since different parts of the same simulation want different acc_tol and you can't determine acc_tol based on accelerations since accelerations can include many different maximas 
        which can lead to an acc_tol which doesn't recognize the lowest or highest maximas. 
        Doesn't work with 3d.

        acc_tol - acc_tol*start acceleration determines what acceleration counts as unusual. Default value 5.
        t_lifetol - t_lifetol*tmax for how close to the end of the simulation a body can turn unactive but still count as active because of uncertainty of what happens after the simulation ends.

        analyse: if False, won't calculate lifespan (useful for example when savetoexcel wants the velocities but doesn't need lifespan)
        """

        G = 6.67430e-11
        m1, m2, m3 = mass[0], mass[1], mass[2]

        ac1x, ac1y, ac2x, ac2y, ac3x, ac3y = [], [], [], [], [], []
        v1, v2, v3 = velocities[0], velocities[1], velocities[2]

        steps = int(steps)

        t = time()

        #Times at which a solution was saved
        t_list = np.linspace(t_start, t_end, steps)
        t_max = t_end-t_start

        lifespan = 0

        ls1 = [0,0]
        ls2 = [0,0]
        ls3 = [0,0]

        #For each step, calculate acceleration on each body and compare to the energy of the moving body.
        for step in range(0, steps):
            x1, y1, x2, y2, x3, y3 = trajectories[0][step], trajectories[1][step], trajectories[2][step], trajectories[3][step], trajectories[4][step], trajectories[5][step]

            pos1 = np.array([x1, y1])
            pos2 = np.array([x2, y2])
            pos3 = np.array([x3, y3])

            pos12 = pos1-pos2
            pos13 = pos1-pos3
            pos23 = pos2-pos3
            dist12 = np.linalg.norm(pos12)
            dist13 = np.linalg.norm(pos13)
            dist23 = np.linalg.norm(pos23)

            #Formula for acceleration on body when two gravitational forces affect a body
            #a1 for force excerted on body 1 from body 2 and 3, and so on...
            a1 = -G * m2 * pos12 / dist12**3 - G * m3 * pos13 / dist13**3
            a2 = -G * m1 * (-pos12) / dist12**3 - G * m3 * pos23 / dist23**3
            a3 = -G * m1 * (-pos13) / dist13**3 - G * m2 * (-pos23) / dist23**3

            #Adding to list for graphing purposes
            ac1x.append(a1[0])
            ac2x.append(a2[0])
            ac3x.append(a3[0])
            ac1y.append(a1[1])
            ac2y.append(a2[1])
            ac3y.append(a3[1])

        if analyse:
            #Turning all accelerations into absolute values
            abs_acc = []
            for acc in ac1x, ac1y, ac2x, ac2y, ac3x, ac3y:
                abs_acc.append([abs(ac) for ac in acc])
            
            starts = [acc[0] for acc in abs_acc]
            #print(starts)

            tols = []
            for start in starts:
                tols.append(start*acc_tol)

            for step in range(0, steps):
                #---Calculating lifespan
                t_current = t_list[step]
                
                #Basically how this works is that we're checking if the acceleration is greater than acc_tol*start acceleration for each body's accelerations to see if a body is still in the system. ls1 can be seen as a "time of death" counter as it 
                #resets every time it's confirmed that the system is alive but as soon as it's not proved to be alive and doesn't already have a saved time of death will become the current time which then acts as the new time of death. 
                if abs_acc[0][step]>tols[0] or abs_acc[1][step]>tols[1]:
                    #Acceleration going away from 0: clear list as the system is not dead yet.
                    ls1 = [0,0]
                else:
                    if ls1 == [0,0]:
                        #If acceleration around 0: add time to list as we want to keep track of the lifespan. 
                        ls1 = [t_current, step+1]
                
                print(tols[2], tols[3])
                if abs_acc[2][step]>tols[2] or abs_acc[3][step]>tols[3]:
                    ls2 = [0,0]
                else:
                    if ls2 == [0,0]:
                        ls2 = [t_current, step+1]
                
                if abs_acc[4][step]>tols[4] or abs_acc[5][step]>tols[5]:
                    ls3 = [0,0]
                else:
                    if ls3 == [0,0]:
                        ls3 = [t_current, step+1]
            print(ls1, ls2, ls3)
            #Convert [0,0] to [t_max,steps] since those with [0,0] has not affected the lifespan
            if ls1 == [0,0]: ls1 = [t_max, steps]
            if ls2 == [0,0]: ls2 = [t_max, steps]
            if ls3 == [0,0]: ls3 = [t_max, steps]

            #Tolerance of how late in the simulation a system can act dead but still be considered alive since we might not be able to tell what happens after the simulation ends.
            #Basically: if time of death is later than the step at which we can't predict the future too well, assume death did not occur.
            tlifetol = t_lifetol*t_max

            if ls1[0]-t_start>tlifetol and ls2[0]-t_start>tlifetol and ls3[0]-t_start>tlifetol:
                lifespan = [t_max, steps]
            else:
                #Choose earliest time of death and set actual time of death by subtracting starting time. 
                lifespan = [min(ls1[0], ls2[0], ls3[0])-t_start,min(ls1[1], ls2[1], ls3[1])]

            print("Lifespan:", lifespan[0], "seconds at step:", lifespan[1])
        calc_time = time()-t
        print("Calculation time:", calc_time)
        
        return ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time
    
    def calculate_lifespan(self, trajectories, velocities, mass, t_start, t_end, steps, save_acc = False, save_vel = False, t_lifetol = 0.9, analyse=True):
        """
        Fourth version. Solution: remove acc_tol altogether. Instead compare last and next values to see if they are greater respectively higher than current acceleration to 
        find maximas in the absolute values of the accelerations. Found a new maxima? Nice, that's our new time of death!
        One problem is that the simulation naturally has small errors which make some random accelerations be larger than the step before and after, so to make sure we get "real" maximas we 
        require that at least one of the jumps is larger than the starting acceleration.

        t_lifetol - t_lifetol*tmax for how close to the end of the simulation a body can turn unactive but still count as active because of uncertainty of what happens after the simulation ends.

        analyse: if False, won't calculate lifespan (useful for example when savetoexcel wants the velocities but doesn't need lifespan)
        """

        G = 6.67430e-11
        m1, m2, m3 = mass[0], mass[1], mass[2]

        ac1x, ac1y, ac2x, ac2y, ac3x, ac3y = [], [], [], [], [], []
        v1, v2, v3 = velocities[0], velocities[1], velocities[2]

        steps = int(steps)

        t = time()

        #Times at which a solution was saved
        t_list = np.linspace(t_start, t_end, steps)
        t_max = t_end-t_start

        lifespan = 0

        ls1 = [0,0]
        ls2 = [0,0]
        ls3 = [0,0]

        #For each step, calculate acceleration on each body and compare to the energy of the moving body.
        for step in range(0, steps):
            x1, y1, x2, y2, x3, y3 = trajectories[0][step], trajectories[1][step], trajectories[2][step], trajectories[3][step], trajectories[4][step], trajectories[5][step]

            pos1 = np.array([x1, y1])
            pos2 = np.array([x2, y2])
            pos3 = np.array([x3, y3])

            pos12 = pos1-pos2
            pos13 = pos1-pos3
            pos23 = pos2-pos3
            dist12 = np.linalg.norm(pos12)
            dist13 = np.linalg.norm(pos13)
            dist23 = np.linalg.norm(pos23)

            #Formula for acceleration on body when two gravitational forces affect a body
            #a1 for force excerted on body 1 from body 2 and 3, and so on...
            a1 = -G * m2 * pos12 / dist12**3 - G * m3 * pos13 / dist13**3
            a2 = -G * m1 * (-pos12) / dist12**3 - G * m3 * pos23 / dist23**3
            a3 = -G * m1 * (-pos13) / dist13**3 - G * m2 * (-pos23) / dist23**3

            #Adding to list for graphing purposes
            ac1x.append(a1[0])
            ac2x.append(a2[0])
            ac3x.append(a3[0])
            ac1y.append(a1[1])
            ac2y.append(a2[1])
            ac3y.append(a3[1])

        if analyse:
            #Turning all accelerations into absolute values
            abs_acc = []
            for acc in ac1x, ac1y, ac2x, ac2y, ac3x, ac3y:
                abs_acc.append([abs(ac) for ac in acc])

            #Starts are used to see if the jump is big enough for the maxima to be called a maxima or if it's just a random small change in acceleration which happens to be higher than the one before and after.
            starts = [acc[0] for acc in abs_acc]

            #---Calculating lifespan
            for step in range(0, steps):
                t_current = t_list[step]
                #Since the system works by looking for AFTER a maximum has occured the lifespan will show one step after the actual occurance of the maximum. That step is then concidered to be the time of death
                
                #Basically how this works is that we're checking if the acceleration is lower the step before and higher the step after for each body's accelerations to see if a body is still in the system. 
                #ls1 can be seen as a "time of death" counter as it resets every time it's confirmed that the system is alive but as soon as it's not proved to be alive and doesn't already have a saved time of death will become the current time which then acts as the new time of death. 
                #First and last step is excluded as they do not have both a step before and step after
                if step != 0 and step != steps-1:
                    if (abs_acc[0][step] > abs_acc[0][step+1] and abs_acc[0][step] > abs_acc[0][step-1] and (abs_acc[0][step]-abs_acc[0][step+1] > starts[0] or abs_acc[0][step]-abs_acc[0][step-1] > starts[0])) or (abs_acc[1][step] > abs_acc[1][step+1] and abs_acc[1][step] > abs_acc[1][step-1] and (abs_acc[1][step]-abs_acc[1][step+1] > starts[1] or abs_acc[1][step]-abs_acc[1][step-1] > starts[1])):
                        #Acceleration at a maximum where one of the jumps are big enough to be a "real" maximum: clear list as the system is not dead yet.
                        ls1 = [0,0]
                        #print(step+1, abs_acc[0][step-1], abs_acc[0][step], abs_acc[0][step+1], abs_acc[1][step-1], abs_acc[1][step], abs_acc[1][step+1])
                    else:
                        if ls1 == [0,0]:
                            #If acceleration around 0: add time to list as we want to keep track of the lifespan. 
                            ls1 = [t_current, step+1]
                    
                    if (abs_acc[2][step] > abs_acc[2][step+1] and abs_acc[2][step] > abs_acc[2][step-1] and (abs_acc[2][step]-abs_acc[2][step+1] > starts[2] or abs_acc[2][step]-abs_acc[2][step-1] > starts[2])) or (abs_acc[3][step] > abs_acc[3][step+1] and abs_acc[3][step] > abs_acc[3][step-1] and (abs_acc[3][step]-abs_acc[3][step+1] > starts[3] or abs_acc[3][step]-abs_acc[3][step-1] > starts[3])):
                        ls2 = [0,0]
                    else:
                        if ls2 == [0,0]:
                            ls2 = [t_current, step+1]
                    
                    if (abs_acc[4][step] > abs_acc[4][step+1] and abs_acc[4][step] > abs_acc[4][step-1] and (abs_acc[4][step]-abs_acc[4][step+1] > starts[4] or abs_acc[4][step]-abs_acc[4][step-1] > starts[4])) or (abs_acc[5][step] > abs_acc[5][step+1] and abs_acc[5][step] > abs_acc[5][step-1] and (abs_acc[5][step]-abs_acc[5][step+1] > starts[5] or abs_acc[5][step]-abs_acc[5][step-1] > starts[5])):
                        ls3 = [0,0]
                    else:
                        if ls3 == [0,0]:
                            ls3 = [t_current, step+1]
            
            #print(ls1, ls2, ls3)
            #Convert [0,0] to [t_max,steps] since those with [0,0] has not affected the lifespan
            if ls1 == [0,0]: ls1 = [t_max, steps]
            if ls2 == [0,0]: ls2 = [t_max, steps]
            if ls3 == [0,0]: ls3 = [t_max, steps]

            #Tolerance of how late in the simulation a system can act dead but still be considered alive since we might not be able to tell what happens after the simulation ends.
            #Basically: if time of death is later than the step at which we can't predict the future too well, assume death did not occur.
            tlifetol = t_lifetol*t_max

            if ls1[0]-t_start>tlifetol and ls2[0]-t_start>tlifetol and ls3[0]-t_start>tlifetol:
                lifespan = [t_max, steps]
            else:
                #Choose earliest time of death and set actual time of death by subtracting starting time. 
                lifespan = [min(ls1[0], ls2[0], ls3[0])-t_start,min(ls1[1], ls2[1], ls3[1])]

            print("Lifespan:", lifespan[0], "seconds at step:", lifespan[1])
        calc_time = time()-t
        print("Calculation time:", calc_time)
        
        return ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time

    def reset(self, bodies):
        self.bodies = bodies

        #Make sure pos and vel are restarted
        for body in self.bodies:
            body.pos = body.startpos
            body.vel = body.startvel

        self.trajectories = []
        self.frames = []
        self.dists = []

    def getSimData(self): return (self.trajectories, self.velocities, len(self.trajectories[0][0]), [body.startpos for body in self.bodies], [body.startvel for body in self.bodies], [body.mass for body in self.bodies], [body.radius for body in self.bodies], [body.color for body in self.bodies], [body.label for body in self.bodies])
    #steps are calculated as len(self.trajectories[0][0]) as collision stops the simulation early.
    def getFrames(self): return self.frames
    def getTrajectories(self): return self.trajectories