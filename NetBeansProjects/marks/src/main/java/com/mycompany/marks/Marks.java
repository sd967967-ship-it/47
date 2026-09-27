/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.marks;

/**
 *
 * @author sd967
 */
import java.util.*;

public class Marks 
    {
    double eng=0,hin=0,math=0,sci=0;
    Scanner in=new Scanner(System.in);
    void input()
    {
       System.out.println("enter marks of english") ;
        eng=in.nextDouble();
        System.out.println("enter marks of maths") ;

        math=in.nextDouble();
        System.out.println("enter marks of hindi") ;

        hin=in.nextDouble();
        System.out.println("enter marks of science") ;

        sci=in.nextDouble();
        
    }
    void calculate()
    {
        double avgmar=0;
        avgmar=hin+eng+math+sci;
        avgmar=avgmar/4;
        if(avgmar>90&&avgmar<100)
        {
            System.out.println("Grade A");
        }
        if(avgmar>70&&avgmar<=90)
        {
            System.out.println("Grade B");
        }
        if(avgmar>50&&avgmar<=70)
        {
            System.out.println("Grade C");
        }
        if(avgmar>35&&avgmar<=50)
        {
            System.out.println("Grade D");
        }
        if(avgmar<=35)
            System.out.println("fail");
        System.out.println("average marks = "+avgmar);
    }
   
        
    

    public static void main(String[] args) {
       Marks ob=new Marks();
       ob.input();
       ob.calculate();
    }
}
